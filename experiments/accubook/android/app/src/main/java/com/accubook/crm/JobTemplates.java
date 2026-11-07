package com.accubook.crm;

import android.util.AtomicFile;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.*;

/**
 * Global job form template, copied into each job at first open and extended
 * non-destructively when the owner adds new defaults. Existing per-job overrides
 * are never overwritten by subsequent master edits.
 */
public final class JobTemplates {
    private static final String[] MASTER={"FieldID","Label","Kind","Required","DefaultValue","Active"};
    private static final String[] JOB={"FieldID","Label","Kind","Required","Value","Active","Origin"};
    public static final String CHECK="Checkbox",TEXT="Text",DATE="Date",NUMBER="Number";
    public static final String[] KINDS={CHECK,TEXT,DATE,NUMBER};
    public static final class Field {
        public final String id,label,kind,value,origin;
        public final boolean required,active;
        Field(List<String> row,boolean job){
            id=row.get(0);label=row.get(1);kind=row.get(2);
            required=Boolean.parseBoolean(row.get(3));value=row.get(4);
            active=Boolean.parseBoolean(row.get(5));
            origin=job?row.get(6):"Master";
        }
        public boolean checked(){return Boolean.parseBoolean(value);}
    }
    private final WorkspaceStore store;
    public JobTemplates(WorkspaceStore workspace){store=workspace;}
    private File masterFile(){return new File(store.root(),"templates/job_fields.csv");}
    private File jobFile(WorkspaceStore.Job job)throws IOException{
        return new File(store.directoryForJob(job),"custom_fields.csv");
    }
    private static List<String> row(String... values){return new ArrayList<>(Arrays.asList(values));}
    private static String id(){return "FIELD-"+UUID.randomUUID().toString().replace("-","");}
    private static String txt(String value,int max,boolean required){
        String input=value==null?"":value.trim();
        if(input.length()>max||(required&&input.isEmpty())||input.indexOf('\0')>=0)
            throw new IllegalArgumentException("Required or invalid job field");
        return input;
    }
    private static String kind(String name){
        if(!Arrays.asList(KINDS).contains(name))throw new IllegalArgumentException("Choose field type");
        return name;
    }
    private static String value(String type,String entered,boolean required){
        String v=txt(entered,type.equals(TEXT)?2000:100,false);
        if(CHECK.equals(type)){
            if(!v.equals("true")&&!v.equals("false"))
                throw new IllegalArgumentException("Checkbox must be checked or unchecked");
        }else if(DATE.equals(type)&&!v.isEmpty()){
            try{LocalDate.parse(v);}
            catch(Exception error){throw new IllegalArgumentException("Date must use YYYY-MM-DD");}
        }else if(NUMBER.equals(type)&&!v.isEmpty()){
            try{
                java.math.BigDecimal n=new java.math.BigDecimal(v);
                if(n.precision()>16)throw new NumberFormatException();
            }catch(NumberFormatException error){throw new IllegalArgumentException("Number invalid");}
        }
        return v;
    }
    private static void write(File path,List<List<String>> rows)throws IOException{
        AtomicFile atomic=new AtomicFile(path);FileOutputStream stream=null;
        try{
            stream=atomic.startWrite();
            stream.write(CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8));
            atomic.finishWrite(stream);
        }catch(IOException|RuntimeException error){
            if(stream!=null)atomic.failWrite(stream);
            throw error;
        }
    }
    private static List<List<String>> read(File path,String[] header)throws IOException{
        if(!path.isFile()&&!new File(path.getPath()+".bak").isFile()){
            List<List<String>> rows=new ArrayList<>();
            rows.add(row(header));write(path,rows);
        }
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(InputStream input=new AtomicFile(path).openRead()){
            byte[] buf=new byte[8192];int n;
            while((n=input.read(buf))!=-1){
                if(bytes.size()+n>4*1024*1024)
                    throw new IOException("Job template exceeds workspace size bound");
                bytes.write(buf,0,n);
            }
        }
        List<List<String>> rows=CsvCodec.read(bytes.toString("UTF-8"));
        if(rows.isEmpty()||!rows.get(0).equals(Arrays.asList(header)))
            throw new IOException("Unknown job field schema");
        for(List<String> r:rows)if(r.size()!=header.length)
            throw new IOException("Malformed job field");
        return rows;
    }
    private static List<List<String>> defaults(){
        List<List<String>> rows=new ArrayList<>();
        rows.add(row(MASTER));
        // Illustrative fields, not required for every contracting trade.
        rows.add(row(id(),"On-site estimate visit",CHECK,"false","false","true"));
        rows.add(row(id(),"Materials delivered",CHECK,"false","false","true"));
        rows.add(row(id(),"Dumpster delivered",CHECK,"false","false","true"));
        rows.add(row(id(),"Dumpster picked up",CHECK,"false","false","true"));
        rows.add(row(id(),"Job-specific instructions",TEXT,"false","","true"));
        return rows;
    }
    private List<List<String>> masterRows()throws IOException{
        File file=masterFile();
        boolean newFile=!file.isFile()&&!new File(file.getPath()+".bak").isFile();
        if(newFile)write(file,defaults());
        return read(file,MASTER);
    }
    public synchronized List<Field> master()throws IOException {
        List<Field> fields=new ArrayList<>();
        List<List<String>> rows=masterRows();
        for(List<String> r:rows.subList(1,rows.size())){
            Field field=new Field(r,false);
            if(field.active)fields.add(field);
        }
        return fields;
    }
    public synchronized void saveMaster(String id,String label,String type,boolean required,
                                        String defaultValue)throws IOException{
        List<List<String>> rows=masterRows();
        String chosen=kind(type);
        String answer=value(chosen,defaultValue,required);
        String key=id==null?id():id;
        if(!key.matches("FIELD-[a-f0-9]{32}"))throw new IOException("Invalid field ID");
        List<String> updated=row(key,txt(label,120,true),chosen,
            Boolean.toString(required),answer,"true");
        int at=-1;
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(key))at=i;
        if(id!=null&&at<0)throw new IOException("Master field not found");
        if(at<0)rows.add(updated);else rows.set(at,updated);
        write(masterFile(),rows);
    }
    public synchronized void removeMaster(String id)throws IOException{
        List<List<String>> rows=masterRows();boolean found=false;
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(id)){
            rows.get(i).set(5,"false");found=true;
        }
        if(!found)throw new IOException("Field not found");
        write(masterFile(),rows);
    }
    private List<List<String>> jobRows(WorkspaceStore.Job job)throws IOException{
        File path=jobFile(job);
        boolean uninitialized=!path.isFile()&&
            !new File(path.getPath()+".bak").isFile();
        if(uninitialized){
            // One-time snapshot: subsequent master changes never unexpectedly
            // add required fields to an existing customer's active job.
            List<List<String>> seed=new ArrayList<>();
            seed.add(row(JOB));
            for(Field defaultField:master()){
                seed.add(row(defaultField.id,defaultField.label,defaultField.kind,
                    Boolean.toString(defaultField.required),defaultField.value,
                    "true","Master"));
            }
            write(path,seed);
        }
        return read(path,JOB);
    }
    public synchronized List<Field> forJob(WorkspaceStore.Job job)throws IOException{
        List<Field> fields=new ArrayList<>();
        List<List<String>> rows=jobRows(job);
        for(List<String> line:rows.subList(1,rows.size())){
            Field field=new Field(line,true);
            if(field.active)fields.add(field);
        }
        return fields;
    }
    public synchronized void saveJob(WorkspaceStore.Job job,String id,String label,
                                     String type,boolean required,String entered)
        throws IOException{
        String kind=kind(type),value=value(kind,entered,required);
        if(!kind.equals(CHECK)&&required&&value.isEmpty()){
            // Allow incomplete required fields: job cannot be marked Completed yet.
        }
        List<List<String>> rows=jobRows(job);
        String key=id==null?id():id;
        if(!key.matches("FIELD-[a-f0-9]{32}"))throw new IOException("Invalid field ID");
        int index=-1;
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(key))index=i;
        if(id!=null&&index<0)throw new IOException("Job field not found");
        String origin=index<0?"Job":rows.get(index).get(6);
        List<String> updated=row(key,txt(label,120,true),kind,
            Boolean.toString(required),value,"true",origin);
        if(index<0)rows.add(updated);else rows.set(index,updated);
        write(jobFile(job),rows);
    }
    public synchronized void removeJob(WorkspaceStore.Job job,String id)throws IOException{
        List<List<String>> rows=jobRows(job);boolean found=false;
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(id)){
            rows.get(i).set(5,"false");found=true;
        }
        if(!found)throw new IOException("Job field not found");
        write(jobFile(job),rows);
    }
    /**
     * Reorders only active fields while retaining inactive rows (tombstones)
     * in their original slots. Stable field IDs, values, and job overrides
     * remain intact. AtomicFile commits the complete reordered CSV.
     */
    private static boolean moveActive(List<List<String>> rows,String fieldId,int newIndex)
        throws IOException {
        List<Integer> slots=new ArrayList<>();
        List<List<String>> active=new ArrayList<>();
        for(int i=1;i<rows.size();i++){
            if("true".equals(rows.get(i).get(5))){
                slots.add(i);
                active.add(rows.get(i));
            }
        }
        int old=-1;
        for(int i=0;i<active.size();i++)
            if(active.get(i).get(0).equals(fieldId)) {old=i;break;}
        if(old<0)throw new IOException("Active field not found");
        if(newIndex<0||newIndex>=active.size())
            throw new IOException("Field destination is out of range");
        if(old==newIndex)return false;
        List<String> moved=active.remove(old);
        active.add(newIndex,moved);
        for(int i=0;i<slots.size();i++)rows.set(slots.get(i),active.get(i));
        return true;
    }

    /** Move a master field; new jobs inherit the new sequence. */
    public synchronized void moveMaster(String id,int newIndex)throws IOException {
        List<List<String>> rows=masterRows();
        if(moveActive(rows,id,newIndex))write(masterFile(),rows);
    }

    /** Move this job's own fields, without changing any other job or master. */
    public synchronized void moveJob(WorkspaceStore.Job job,String id,int newIndex)
        throws IOException {
        List<List<String>> rows=jobRows(job);
        if(moveActive(rows,id,newIndex))write(jobFile(job),rows);
    }

    public synchronized List<String> missingRequired(WorkspaceStore.Job job)throws IOException{
        List<String> missing=new ArrayList<>();
        for(Field f:forJob(job))if(f.required){
            boolean incomplete=f.kind.equals(CHECK)?!f.checked():f.value.trim().isEmpty();
            if(incomplete)missing.add(f.label);
        }
        return missing;
    }
}
