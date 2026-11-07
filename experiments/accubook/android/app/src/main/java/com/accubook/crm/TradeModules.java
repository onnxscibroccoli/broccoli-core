package com.accubook.crm;

import android.util.AtomicFile;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Additive, trade-agnostic pricebook and operational milestones.
 * Never silently updates existing invoice lines after a pricebook change.
 */
public final class TradeModules {
    private final WorkspaceStore store;
    private static final String[] PRICE_HEADER={
        "CatalogID","Category","Name","Unit","BaseCost","MarkupPercent","Supplier","UpdatedUTC"
    };
    private static final String[] MILESTONE_HEADER={"Key","Name","Complete","CompletedUTC","Notes"};
    private static final String[] LOGISTICS_HEADER={
        "Vendor","MaterialDeliveryContact","AssignedCrew","OperationsNotes"
    };
    public static final String[] DEFAULT_MILESTONES={
        "Dumpster delivered","Materials delivered","Dumpster picked up"
    };
    public static final class CatalogItem {
        public final String id,category,name,unit,cost,markup,supplier,updated;
        CatalogItem(List<String> fields){
            id=fields.get(0);category=fields.get(1);name=fields.get(2);unit=fields.get(3);
            cost=fields.get(4);markup=fields.get(5);
            supplier=fields.get(6);updated=fields.get(7);
        }
        public String price(){
            return PricingEngine.price(new BigDecimal(cost),new BigDecimal(markup))
                .toPlainString();
        }
        public String label(){return name+" · "+unit+" · $"+price();}
    }
    public static final class Milestone {
        public final String key,name,finished,date,notes;
        Milestone(List<String> r){key=r.get(0);name=r.get(1);finished=r.get(2);
            date=r.get(3);notes=r.get(4);}
        public boolean complete(){return "true".equals(finished);}
    }
    public static final class Logistics {
        public final String vendor,delivery,crew,notes;
        Logistics(List<String> r){vendor=r.get(0);delivery=r.get(1);
            crew=r.get(2);notes=r.get(3);}
    }
    public TradeModules(WorkspaceStore store){this.store=store;}
    private static List<String> r(String... values){
        return new ArrayList<>(Arrays.asList(values));
    }
    private static List<List<String>> blank(String[] header){
        List<List<String>> result=new ArrayList<>();
        result.add(r(header));return result;
    }
    private static void write(File file,List<List<String>> rows)throws IOException{
        File parent=file.getParentFile();
        if(!parent.isDirectory()&&!parent.mkdirs())throw new IOException("Cannot create directory");
        byte[] data=CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8);
        AtomicFile atomic=new AtomicFile(file);
        FileOutputStream out=null;
        try{out=atomic.startWrite();out.write(data);atomic.finishWrite(out);}
        catch(IOException|RuntimeException e){if(out!=null)atomic.failWrite(out);throw e;}
    }
    private static List<List<String>> read(File file,String[] header)throws IOException{
        if(!file.isFile()&&!new File(file.getPath()+".bak").exists())write(file,blank(header));
        ByteArrayOutputStream data=new ByteArrayOutputStream();
        try(InputStream stream=new AtomicFile(file).openRead()){
            byte[] bytes=new byte[8192];int n;
            while((n=stream.read(bytes))!=-1){
                if(data.size()+n>4*1024*1024)throw new IOException("Pricebook/table too large");
                data.write(bytes,0,n);
            }
        }
        List<List<String>> rows=CsvCodec.read(data.toString("UTF-8"));
        if(rows.isEmpty()||!rows.get(0).equals(Arrays.asList(header)))
            throw new IOException("Unexpected schema: "+file.getName());
        for(List<String> row:rows)if(row.size()!=header.length)
            throw new IOException("Malformed row in "+file.getName());
        return rows;
    }
    private static String txt(String value,int max,boolean required){
        String s=value==null?"":value.trim();
        if(s.length()>max||(required&&s.isEmpty())||s.indexOf('\0')>=0)
            throw new IllegalArgumentException("Required or oversized text");
        return s;
    }
    private static String uuid(){return UUID.randomUUID().toString().replace("-","");}
    private File priceFile(){return new File(store.root(),"master_data/pricebook.csv");}
    private File milestonesFile(WorkspaceStore.Job job)throws IOException{
        return new File(store.directoryForJob(job),"job_milestones.csv");
    }
    private File logisticsFile(WorkspaceStore.Job job)throws IOException{
        return new File(store.directoryForJob(job),"job_logistics.csv");
    }
    public synchronized List<CatalogItem> catalog()throws IOException{
        File file=priceFile();
        List<List<String>> rows=read(file,PRICE_HEADER);
        if(rows.size()==1){
            String now=java.time.Instant.now().toString();
            // Starter prices are editable examples, not supplier quotes.
            rows.add(r("CAT-"+uuid(),"Gutter Cleaning","Standard gutter cleaning",
                "service","250.00","0","Manual",now));
            rows.add(r("CAT-"+uuid(),"Gutter Cleaning","Downspout flush (first)",
                "service","50.00","0","Manual",now));
            rows.add(r("CAT-"+uuid(),"Gutter Cleaning","Additional downspout",
                "each","10.00","0","Manual",now));
            rows.add(r("CAT-"+uuid(),"Carpentry","Fence panel","each","45.00",
                "20","Manual",now));
            rows.add(r("CAT-"+uuid(),"Carpentry","Fence post","each","18.00",
                "25","Manual",now));
            write(file,rows);
        }
        List<CatalogItem> items=new ArrayList<>();
        for(int i=1;i<rows.size();i++)items.add(new CatalogItem(rows.get(i)));
        return items;
    }
    public synchronized CatalogItem saveItem(String id,String category,String name,String unit,
                                           String baseline,String markup,String supplier)
        throws IOException{
        BigDecimal cost=CrmWorkspace.money(txt(baseline,32,true),false);
        if(cost.signum()<0)throw new IllegalArgumentException("Base cost cannot be negative");
        BigDecimal percent;
        try{percent=new BigDecimal(txt(markup,15,true));}
        catch(NumberFormatException e){throw new IllegalArgumentException("Invalid markup percentage");}
        PricingEngine.price(cost,percent);
        String itemId=id==null?"CAT-"+uuid():txt(id,36,true);
        if(!itemId.matches("CAT-[a-f0-9]{32}"))throw new IOException("Invalid catalog ID");
        List<String> value=r(itemId,txt(category,100,true),txt(name,180,true),
            txt(unit,40,true),cost.toPlainString(),percent.toPlainString(),
            txt(supplier,80,false),java.time.Instant.now().toString());
        File file=priceFile();
        List<List<String>> rows=read(file,PRICE_HEADER);
        int existing=-1;
        for(int i=1;i<rows.size();i++)
            if(rows.get(i).get(0).equals(itemId))existing=i;
        if(id!=null&&existing<0)throw new IOException("Catalog item no longer exists");
        if(existing<0)rows.add(value);else rows.set(existing,value);
        write(file,rows);
        return new CatalogItem(value);
    }
    public synchronized List<Milestone> milestones(WorkspaceStore.Job job)throws IOException{
        File file=milestonesFile(job);
        List<List<String>> rows=read(file,MILESTONE_HEADER);
        if(rows.size()==1){
            for(String name:DEFAULT_MILESTONES)
                rows.add(r("MILE-"+uuid(),name,"false","",""));
            write(file,rows);
        }
        List<Milestone> result=new ArrayList<>();
        for(int i=1;i<rows.size();i++)result.add(new Milestone(rows.get(i)));
        return result;
    }
    public synchronized Milestone addMilestone(WorkspaceStore.Job job,String name)
        throws IOException{
        File file=milestonesFile(job);
        milestones(job);
        List<List<String>> rows=read(file,MILESTONE_HEADER);
        List<String> entry=r("MILE-"+uuid(),txt(name,120,true),"false","","");
        rows.add(entry);write(file,rows);
        return new Milestone(entry);
    }
    public synchronized void setMilestone(WorkspaceStore.Job job,String key,
                                          boolean completed,String notes)throws IOException{
        File file=milestonesFile(job);
        List<List<String>> rows=read(file,MILESTONE_HEADER);
        boolean found=false;
        for(int i=1;i<rows.size();i++){
            List<String> row=rows.get(i);
            if(row.get(0).equals(key)){
                row.set(2,Boolean.toString(completed));
                row.set(3,completed?java.time.Instant.now().toString():"");
                row.set(4,txt(notes,1000,false));
                found=true;break;
            }
        }
        if(!found)throw new IOException("Milestone no longer exists");
        write(file,rows);
    }
    public synchronized Logistics logistics(WorkspaceStore.Job job)throws IOException{
        List<List<String>> rows=read(logisticsFile(job),LOGISTICS_HEADER);
        if(rows.size()>2)throw new IOException("Repeated logistics record");
        return rows.size()==1?new Logistics(r("","","","")):new Logistics(rows.get(1));
    }
    public synchronized void saveLogistics(WorkspaceStore.Job job,String vendor,
                                           String delivery,String crew,String notes)
        throws IOException{
        List<List<String>> rows=blank(LOGISTICS_HEADER);
        rows.add(r(txt(vendor,120,false),txt(delivery,120,false),txt(crew,200,false),
            txt(notes,2000,false)));
        write(logisticsFile(job),rows);
    }
}
