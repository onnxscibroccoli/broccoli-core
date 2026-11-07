package com.accubook.crm;

import android.util.AtomicFile;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Local-only inventory repository. Item catalog writes one CSV; every stock
 * movement is ONE atomic append (one debit + one credit in a single row).
 * No background network, no destructive synchronization, no hidden balances.
 */
public final class InventoryStore {
    private final WorkspaceStore store;
    private final File itemFile,moveFile;
    public InventoryStore(WorkspaceStore workspace) {
        store=workspace;
        File master=new File(workspace.root(),"master_data");
        itemFile=new File(master,"inventory_items.csv");
        moveFile=new File(master,"inventory_movements.csv");
    }
    private static List<String> row(String... values){
        return new ArrayList<>(Arrays.asList(values));
    }
    private static List<List<String>> fresh(String[] header){
        List<List<String>> rows=new ArrayList<>();
        rows.add(row(header));
        return rows;
    }
    private static void write(File file,List<List<String>> rows) throws IOException {
        AtomicFile atomic=new AtomicFile(file);
        FileOutputStream stream=null;
        try{
            stream=atomic.startWrite();
            stream.write(CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8));
            atomic.finishWrite(stream);
        }catch(IOException|RuntimeException error){
            if(stream!=null)atomic.failWrite(stream);
            throw error;
        }
    }
    private static List<List<String>> read(File file,String[] header) throws IOException {
        if(!file.isFile()&&!new File(file.getPath()+".bak").isFile())
            return fresh(header);
        AtomicFile atomic=new AtomicFile(file);
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        try(InputStream stream=atomic.openRead()){
            byte[] chunk=new byte[8192];int n;
            while((n=stream.read(chunk))!=-1){
                if(out.size()+n>4*1024*1024)
                    throw new IOException("Inventory file exceeds safety limit");
                out.write(chunk,0,n);
            }
        }
        String csv=out.toString("UTF-8");
        List<List<String>> rows=CsvCodec.read(csv);
        if(rows.isEmpty()||!rows.get(0).equals(Arrays.asList(header)))
            throw new IOException("Unsupported inventory data version");
        for(List<String> record:rows)if(record.size()!=header.length)
            throw new IOException("Malformed inventory data");
        return rows;
    }
    private Set<String> jobs()throws IOException{
        Set<String> found=new HashSet<>();
        for(WorkspaceStore.Job job:store.jobs())found.add(job.id);
        return found;
    }
    public synchronized StockLedger.State state()throws IOException{
        return StockLedger.validate(read(itemFile,StockLedger.ITEMS),
            read(moveFile,StockLedger.MOVES),jobs());
    }
    private static String text(String s,int max,String title) throws IOException{
        String value=s==null?"":s.trim();
        if(value.length()==0||value.length()>max||value.indexOf('\0')>=0)
            throw new IOException("Inventory: invalid "+title);
        return value;
    }
    /** An inventory item has zero stock until a receipt or adjustment is logged. */
    public synchronized String addItem(String label,String kind,String unit) throws IOException {
        String name=text(label,180,"name"), u=text(unit,40,"unit");
        if(!kind.equals(StockLedger.MATERIAL)&&!kind.equals(StockLedger.TOOL))
            throw new IOException("Choose material or tool");
        List<List<String>> items=read(itemFile,StockLedger.ITEMS);
        List<List<String>> moves=read(moveFile,StockLedger.MOVES);
        String id="INV-"+UUID.randomUUID().toString().replace("-","");
        items.add(row(id,name,kind,u,"true"));
        StockLedger.validate(items,moves,jobs());
        write(itemFile,items);
        return id;
    }
    /**
     * Append exactly one immutable event after replaying the full ledger.
     * A failed validation cannot change stock. Never delete history to fix it:
     * record a compensating transaction with an explanation instead.
     */
    public synchronized void move(String itemId,String action,String from,String to,
                                  String quantity,String note) throws IOException {
        List<List<String>> items=read(itemFile,StockLedger.ITEMS);
        List<List<String>> moves=read(moveFile,StockLedger.MOVES);
        String reason=note==null?"":note.trim();
        if(reason.length()>250||reason.indexOf('\0')>=0)
            throw new IOException("Inventory reason exceeds 250 characters");
        moves.add(row("MOVE-"+UUID.randomUUID().toString().replace("-",""),
            itemId,Instant.now().toString(),action,from,to,quantity,reason));
        StockLedger.validate(items,moves,jobs());
        write(moveFile,moves);
    }
}
