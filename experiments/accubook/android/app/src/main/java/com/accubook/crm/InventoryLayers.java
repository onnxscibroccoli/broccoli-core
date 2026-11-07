package com.accubook.crm;

import android.util.AtomicFile;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Optional, local-only, 3-layer inventory: company materials, job-site
 * delivered/used/returned observations, and assigned tools. These tables do
 * not auto-decrement company stock or post invoice/expense entries. This avoids
 * silently duplicating financial or stock transactions across CSV files.
 */
public final class InventoryLayers {
    public static final class Material {
        public final String id,name,unit,onHand,cost,catalogId;
        Material(List<String> row){
            id=row.get(0);name=row.get(1);unit=row.get(2);
            onHand=row.get(3);cost=row.get(4);catalogId=row.get(5);
        }
    }
    public static final class SiteEntry {
        public final String id,name,unit,quantity,status;
        SiteEntry(List<String> row){
            id=row.get(0);name=row.get(1);unit=row.get(2);
            quantity=row.get(3);status=row.get(4);
        }
    }
    public static final class Tool {
        public final String id,name,assetTag,status,jobId;
        Tool(List<String> row){
            id=row.get(0);name=row.get(1);assetTag=row.get(2);
            status=row.get(3);jobId=row.get(4);
        }
    }
    private final WorkspaceStore store;
    public InventoryLayers(WorkspaceStore store){this.store=store;}
    private static String uid(String prefix){
        return prefix+"-"+UUID.randomUUID().toString().replace("-","");
    }
    private static List<String> row(String... fields){
        return new ArrayList<>(Arrays.asList(fields));
    }
    private static List<List<String>> empty(String[] header){
        List<List<String>> result=new ArrayList<>();result.add(row(header));return result;
    }
    private File companyFile(){return new File(store.root(),"master_data/inventory_materials.csv");}
    private File toolsFile(){return new File(store.root(),"master_data/inventory_tools.csv");}
    private File siteFile(WorkspaceStore.Job job)throws IOException{
        return new File(store.directoryForJob(job),"job_site_materials.csv");
    }
    private static void write(File file,List<List<String>> rows)throws IOException{
        File parent=file.getParentFile();
        if(!parent.isDirectory()&&!parent.mkdirs())throw new IOException("Cannot create inventory folder");
        byte[] data=CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8);
        if(data.length>4*1024*1024)throw new IOException("Inventory table exceeds 4 MB");
        AtomicFile atomic=new AtomicFile(file);FileOutputStream out=null;
        try{
            out=atomic.startWrite();out.write(data);atomic.finishWrite(out);
        }catch(IOException|RuntimeException error){
            if(out!=null)atomic.failWrite(out);
            throw error;
        }
    }
    private static List<List<String>> read(File file,String[] header,int type)
        throws IOException {
        if(!file.isFile()&&!new File(file.getPath()+".bak").isFile())
            write(file,empty(header));
        ByteArrayOutputStream output=new ByteArrayOutputStream();
        try(InputStream in=new AtomicFile(file).openRead()){
            byte[] chunk=new byte[8192];int n;
            while((n=in.read(chunk))!=-1){
                if(output.size()+n>4*1024*1024)throw new IOException("Inventory CSV too large");
                output.write(chunk,0,n);
            }
        }
        List<List<String>> rows=CsvCodec.read(output.toString("UTF-8"));
        if(rows.isEmpty()||!rows.get(0).equals(Arrays.asList(header))||rows.size()>2001)
            throw new IOException("Invalid inventory schema or record limit");
        Set<String> ids=new HashSet<>();
        for(int i=1;i<rows.size();i++){
            try{
                List<String> entry=rows.get(i);
                if(type==0)InventoryRules.company(entry);
                else if(type==1)InventoryRules.site(entry);
                else InventoryRules.tool(entry);
                if(!ids.add(entry.get(0)))throw new IOException("Repeated inventory ID");
            }catch(IllegalArgumentException invalid){
                throw new IOException("Invalid inventory entry at row "+(i+1),invalid);
            }
        }
        return rows;
    }
    private static List<String> located(List<List<String>> rows,String id)throws IOException{
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(id))return rows.get(i);
        throw new IOException("Inventory record not found");
    }
    private static void replace(List<List<String>> rows,List<String> entry,String id)
        throws IOException {
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(id)){
            rows.set(i,entry);return;
        }
        throw new IOException("Inventory record was removed; reopen the list");
    }
    private static void remove(List<List<String>> rows,String id)throws IOException{
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(id)){
            rows.remove(i);return;
        }
        throw new IOException("Inventory record was removed; reopen the list");
    }
    private static String checkedId(String id,String prefix){
        if(id==null||!id.matches(prefix+"-[a-f0-9]{32}"))
            throw new IllegalArgumentException("Invalid inventory record");
        return id;
    }
    private void verifyJob(WorkspaceStore.Job job)throws IOException{
        boolean found=false;
        for(WorkspaceStore.Job current:store.jobs())
            if(current.id.equals(job.id)&&current.customerId.equals(job.customerId)){
                found=true;break;
            }
        if(!found)throw new IOException("Job is no longer present");
    }

    public synchronized List<Material> companyMaterials()throws IOException{
        List<Material> result=new ArrayList<>();
        for(List<String> entry:read(companyFile(),InventoryRules.COMPANY,0).subList(1,
            read(companyFile(),InventoryRules.COMPANY,0).size()))
            result.add(new Material(entry));
        return result;
    }
    public synchronized Material saveMaterial(String existingId,String name,String unit,
            String onHand,String cost,String catalogId)throws IOException{
        String id=existingId==null?uid("MAT"):checkedId(existingId,"MAT");
        List<String> value=row(id,InventoryRules.text(name,160,true),
            InventoryRules.text(unit,40,true),InventoryRules.quantity(onHand,true),
            InventoryRules.cost(cost),InventoryRules.text(catalogId,40,false));
        InventoryRules.company(value);
        File file=companyFile();List<List<String>> rows=read(file,InventoryRules.COMPANY,0);
        if(existingId==null)rows.add(value);else replace(rows,value,id);
        write(file,rows);return new Material(value);
    }
    public synchronized void deleteMaterial(String id)throws IOException{
        File file=companyFile();List<List<String>> rows=read(file,InventoryRules.COMPANY,0);
        remove(rows,checkedId(id,"MAT"));write(file,rows);
    }

    public synchronized List<SiteEntry> siteMaterials(WorkspaceStore.Job job)throws IOException{
        verifyJob(job);
        File file=siteFile(job);List<List<String>> rows=read(file,InventoryRules.SITE,1);
        List<SiteEntry> result=new ArrayList<>();
        for(int i=1;i<rows.size();i++)result.add(new SiteEntry(rows.get(i)));
        return result;
    }
    public synchronized SiteEntry saveSite(WorkspaceStore.Job job,String existingId,
            String name,String unit,String quantity,String status)throws IOException{
        verifyJob(job);
        String id=existingId==null?uid("SITE"):checkedId(existingId,"SITE");
        List<String> value=row(id,InventoryRules.text(name,160,true),
            InventoryRules.text(unit,40,true),InventoryRules.quantity(quantity,false),status);
        InventoryRules.site(value);
        File file=siteFile(job);List<List<String>> rows=read(file,InventoryRules.SITE,1);
        if(existingId==null)rows.add(value);else replace(rows,value,id);
        write(file,rows);return new SiteEntry(value);
    }
    public synchronized void deleteSite(WorkspaceStore.Job job,String id)throws IOException{
        verifyJob(job);
        File file=siteFile(job);List<List<String>> rows=read(file,InventoryRules.SITE,1);
        remove(rows,checkedId(id,"SITE"));write(file,rows);
    }

    public synchronized List<Tool> tools()throws IOException{
        File file=toolsFile();List<List<String>> rows=read(file,InventoryRules.TOOLS,2);
        List<Tool> result=new ArrayList<>();
        for(int i=1;i<rows.size();i++)result.add(new Tool(rows.get(i)));
        return result;
    }
    public synchronized Tool saveTool(String existingId,String name,String assetTag)
        throws IOException{
        File file=toolsFile();List<List<String>> rows=read(file,InventoryRules.TOOLS,2);
        String id=existingId==null?uid("TOOL"):checkedId(existingId,"TOOL");
        String status="Available",jobId="";
        if(existingId!=null){
            List<String> previous=located(rows,id);
            status=previous.get(3);jobId=previous.get(4);
        }
        List<String> value=row(id,InventoryRules.text(name,160,true),
            InventoryRules.text(assetTag,100,false),status,jobId);
        InventoryRules.tool(value);
        if(existingId==null)rows.add(value);else replace(rows,value,id);
        write(file,rows);return new Tool(value);
    }
    public synchronized void setToolState(String id,String state,WorkspaceStore.Job job)
        throws IOException{
        File file=toolsFile();List<List<String>> rows=read(file,InventoryRules.TOOLS,2);
        List<String> previous=located(rows,checkedId(id,"TOOL"));
        if(!InventoryRules.TOOL_STATES.contains(state))
            throw new IllegalArgumentException("Unknown equipment state");
        if("Checked Out".equals(state)){
            if(job==null)throw new IllegalArgumentException("Choose a job");
            verifyJob(job);
            if(!"Available".equals(previous.get(3)) &&
                !("Checked Out".equals(previous.get(3))&&job.id.equals(previous.get(4))))
                throw new IOException("Tool is unavailable; return or repair it first");
        }
        previous.set(3,state);
        previous.set(4,"Checked Out".equals(state)?job.id:"");
        InventoryRules.tool(previous);
        write(file,rows);
    }
    public synchronized void deleteTool(String id)throws IOException{
        File file=toolsFile();List<List<String>> rows=read(file,InventoryRules.TOOLS,2);
        List<String> old=located(rows,checkedId(id,"TOOL"));
        if("Checked Out".equals(old.get(3)))
            throw new IOException("Return the tool before deleting its record");
        remove(rows,id);write(file,rows);
    }
}
