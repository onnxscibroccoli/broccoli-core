package com.accubook.crm;

import android.graphics.BitmapFactory;
import android.util.AtomicFile;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Job-linked change orders, with separately captured acknowledgement.
 * Per-file atomic CSV writes. Multi-file transactions are recoverable but
 * not all-or-nothing. Billing is explicitly initiated and idempotent by line tag.
 */
public final class ChangeOrders {
    public static final String[] ORDERS={
        "ChangeOrderID","Title","Status","CreatedUTC","AcknowledgedUTC",
        "SignedBy","SignatureSHA256","ContentSHA256"
    };
    public static final String[] LINES={
        "LineID","ChangeOrderID","Description","Quantity","UnitRate","Amount"
    };
    public static final String PROPOSED="Proposed";
    public static final String ACKNOWLEDGED="Acknowledged";
    public static final String INVOICED="Invoiced";
    private final WorkspaceStore store;

    public static final class Order {
        public final String id,title,status,created,acknowledged,signedBy,signatureHash,contentHash;
        Order(List<String> r) {
            id=r.get(0);title=r.get(1);status=r.get(2);created=r.get(3);
            acknowledged=r.get(4);signedBy=r.get(5);
            signatureHash=r.get(6);contentHash=r.get(7);
        }
        public boolean signed(){return !PROPOSED.equals(status);}
    }
    public static final class Line {
        public final String id,orderId,description,quantity,rate,amount;
        Line(List<String> r) {
            id=r.get(0);orderId=r.get(1);description=r.get(2);
            quantity=r.get(3);rate=r.get(4);amount=r.get(5);
        }
    }
    public ChangeOrders(WorkspaceStore store){this.store=store;}
    private static String uuid(String prefix) {
        return prefix+UUID.randomUUID().toString().replace("-","");
    }
    private static String txt(String value,int limit,boolean required) {
        String s=value==null?"":value.trim();
        if(s.length()>limit || (required&&s.isEmpty()))throw new IllegalArgumentException(
            "Required or oversized entry");
        for(int i=0;i<s.length();i++)
            if(Character.isISOControl(s.charAt(i)))
                throw new IllegalArgumentException("Control character in entry");
        return s;
    }
    private static List<String> row(String... values){
        return new ArrayList<>(Arrays.asList(values));
    }
    private static List<List<String>> blank(String[] h){
        List<List<String>> out=new ArrayList<>();
        out.add(row(h));return out;
    }
    private static byte[] readBytes(File f,int max) throws IOException {
        ByteArrayOutputStream data=new ByteArrayOutputStream();
        try(InputStream in=new AtomicFile(f).openRead()){
            byte[] b=new byte[8192];int n;
            while((n=in.read(b))!=-1) {
                if(data.size()+(long)n>max)throw new IOException("Change-order file exceeds limit");
                data.write(b,0,n);
            }
        }
        return data.toByteArray();
    }
    private static void atomic(File f,byte[] data) throws IOException {
        File parent=f.getParentFile();
        if(!parent.isDirectory()&&!parent.mkdirs())throw new IOException("Cannot create local folder");
        AtomicFile a=new AtomicFile(f);FileOutputStream out=null;
        try{
            out=a.startWrite();out.write(data);a.finishWrite(out);
        }catch(IOException|RuntimeException error){
            if(out!=null)a.failWrite(out);
            throw error;
        }
    }
    private static List<List<String>> table(File f,String[] header)throws IOException {
        if(!f.isFile()&&!new File(f.getPath()+".bak").isFile())
            atomic(f,CsvCodec.write(blank(header)).getBytes(StandardCharsets.UTF_8));
        List<List<String>> rows=CsvCodec.read(new String(readBytes(f,4*1024*1024),
            StandardCharsets.UTF_8));
        if(rows.isEmpty()||!rows.get(0).equals(Arrays.asList(header))||rows.size()>1001)
            throw new IOException("Unexpected change-order CSV schema or count");
        for(List<String> row:rows)if(row.size()!=header.length)
            throw new IOException("Malformed change-order CSV row");
        return rows;
    }
    private static void write(File f,List<List<String>> rows) throws IOException {
        if(rows.size()>1001)throw new IOException("Too many change orders or lines");
        atomic(f,CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8));
    }
    private File file(WorkspaceStore.Job job,String name) throws IOException {
        return new File(store.directoryForJob(job),name);
    }
    private File signature(WorkspaceStore.Job job,String id)throws IOException {
        if(!id.matches("CO-[a-f0-9]{32}"))throw new IOException("Invalid change order ID");
        return file(job,"change_order_signatures/"+id+".png");
    }
    private List<List<String>> orderRows(WorkspaceStore.Job job)throws IOException {
        return table(file(job,"change_orders.csv"),ORDERS);
    }
    private List<List<String>> lineRows(WorkspaceStore.Job job)throws IOException {
        return table(file(job,"change_order_lines.csv"),LINES);
    }
    private static List<String> locate(List<List<String>> rows,String id)throws IOException {
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(id))return rows.get(i);
        throw new IOException("Change order no longer exists");
    }
    private static List<List<String>> subset(List<List<String>> rows,String id) {
        List<List<String>> list=new ArrayList<>();
        for(int i=1;i<rows.size();i++)
            if(rows.get(i).get(1).equals(id))list.add(new ArrayList<>(rows.get(i)));
        return list;
    }
    public synchronized List<Order> orders(WorkspaceStore.Job job)throws IOException {
        List<List<String>> rows=orderRows(job);
        List<Order> out=new ArrayList<>();Set<String> ids=new HashSet<>();
        for(int i=1;i<rows.size();i++){
            Order order=new Order(rows.get(i));
            if(!order.id.matches("CO-[a-f0-9]{32}")||!ids.add(order.id) ||
                !(PROPOSED.equals(order.status)||ACKNOWLEDGED.equals(order.status)||
                    INVOICED.equals(order.status)))
                throw new IOException("Invalid change order ID or status");
            if(order.signed())verify(job,order);
            out.add(order);
        }
        return out;
    }
    public synchronized Order create(WorkspaceStore.Job job,String title)throws IOException {
        File f=file(job,"change_orders.csv");
        List<List<String>> rows=orderRows(job);
        List<String> r=row(uuid("CO-"),txt(title,160,true),PROPOSED,
            Instant.now().toString(),"","","","");
        rows.add(r);write(f,rows);
        return new Order(r);
    }
    public synchronized List<Line> lines(WorkspaceStore.Job job,Order order)throws IOException {
        List<Line> out=new ArrayList<>();
        for(List<String> l:subset(lineRows(job),order.id)) {
            ChangeOrderProof.total(java.util.Collections.singletonList(l));
            out.add(new Line(l));
        }
        return out;
    }
    public synchronized String total(WorkspaceStore.Job job,Order order)throws IOException {
        return ChangeOrderProof.total(subset(lineRows(job),order.id));
    }
    public synchronized Line addLine(WorkspaceStore.Job job,Order order,
            String description,String quantity,String rate)throws IOException {
        List<List<String>> orders=orderRows(job);
        if(!PROPOSED.equals(locate(orders,order.id).get(2)))
            throw new IOException("Signed change orders cannot be edited; create a new one");
        String desc=txt(description,176,true);
        String qty=txt(quantity,32,true),unit=txt(rate,32,true);
        if(new BigDecimal(unit).signum()<0 &&
            !desc.toLowerCase(java.util.Locale.ROOT).contains("discount"))
            throw new IllegalArgumentException("Negative rates require a discount description");
        String amount=ChangeOrderProof.amount(qty,unit);
        List<String> r=row(uuid("COL-"),order.id,desc,qty,unit,amount);
        File f=file(job,"change_order_lines.csv");
        List<List<String>> rows=lineRows(job); rows.add(r);write(f,rows);
        return new Line(r);
    }
    /**
     * Save PNG first; index record is the commit marker. An interrupted write
     * may leave an unreferenced PNG, but never a valid acknowledged order with
     * a missing signature.
     */
    public synchronized Order acknowledge(WorkspaceStore.Job job,Order order,
            String signer,byte[] png)throws IOException {
        String name=txt(signer,120,true);
        if(png==null||png.length<100||png.length>256*1024)
            throw new IOException("Signature image must be 100 bytes–256 KB");
        byte[] magic={(byte)137,80,78,71,13,10,26,10};
        for(int i=0;i<magic.length;i++)if(png[i]!=magic[i])
            throw new IOException("Signature must be PNG");
        BitmapFactory.Options options=new BitmapFactory.Options();options.inJustDecodeBounds=true;
        BitmapFactory.decodeByteArray(png,0,png.length,options);
        if(options.outWidth<64||options.outHeight<40||options.outWidth>1600||
            options.outHeight>1600)throw new IOException("Invalid signature dimensions");
        List<List<String>> orders=orderRows(job);
        List<String> current=locate(orders,order.id);
        if(!PROPOSED.equals(current.get(2)))throw new IOException("Already acknowledged");
        List<List<String>> lines=subset(lineRows(job),order.id);
        if(lines.isEmpty())throw new IOException("Add work lines before asking for signature");
        ChangeOrderProof.total(lines);
        String time=Instant.now().toString(),sigHash=ChangeOrderProof.sha256(png);
        String hash=ChangeOrderProof.contentHash(job.id,order.id,current.get(1),
            time,name,sigHash,lines);
        atomic(signature(job,order.id),png);
        current.set(2,ACKNOWLEDGED);current.set(4,time);current.set(5,name);
        current.set(6,sigHash);current.set(7,hash);
        write(file(job,"change_orders.csv"),orders);
        return new Order(current);
    }
    /** Always re-check the signed snapshot before displaying or billing. */
    public synchronized void verify(WorkspaceStore.Job job,Order order)throws IOException {
        if(!order.signed())return;
        byte[] png=readBytes(signature(job,order.id),256*1024);
        if(!ChangeOrderProof.sha256(png).equals(order.signatureHash))
            throw new IOException("Change-order signature has changed");
        List<List<String>> lines=subset(lineRows(job),order.id);
        try {
            ChangeOrderProof.total(lines);
            String hash=ChangeOrderProof.contentHash(job.id,order.id,order.title,
                order.acknowledged,order.signedBy,order.signatureHash,lines);
            if(!hash.equals(order.contentHash))
                throw new IOException("Signed change-order content has changed");
        }catch(IllegalArgumentException e){
            throw new IOException("Invalid signed change-order lines",e);
        }
    }
    /**
     * Adds canonical billing lines once. A crash after a line append is
     * recoverable: the next call checks exact stable line tags before appending.
     */
    public synchronized void addToInvoice(WorkspaceStore.Job job,Order order)throws IOException {
        List<List<String>> orders=orderRows(job);
        List<String> current=locate(orders,order.id);
        if(INVOICED.equals(current.get(2)))return;
        if(!ACKNOWLEDGED.equals(current.get(2)))
            throw new IOException("Customer acknowledgement is required before billing");
        verify(job,new Order(current));
        List<List<String>> lines=subset(lineRows(job),order.id);
        for(List<String> line:lines) {
            String tag="[CO:"+line.get(0)+"]";
            boolean present=false;
            for(WorkspaceStore.LineItem existing:store.items(job))
                if(existing.description.endsWith(tag))present=true;
            if(!present) store.addLine(job,line.get(2)+" "+tag,line.get(3),line.get(4));
        }
        current.set(2,INVOICED);
        write(file(job,"change_orders.csv"),orders);
    }
}
