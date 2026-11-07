package com.accubook.crm;

import android.util.AtomicFile;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * Private address book, independent of customers. Importing a contact never
 * creates a customer or a job. One CSV commit per batch preserves atomicity.
 */
public final class ContactDirectory {
    private static final String[] HEADER={"ContactID","Name","Phone","Email","SourceID","CustomerID"};
    public static final class Contact {
        public final String id,name,phone,email,source,customerId;
        Contact(List<String> r) {
            id=r.get(0);name=r.get(1);phone=r.get(2);email=r.get(3);
            source=r.get(4);customerId=r.get(5);
        }
    }
    public static final class ImportEntry {
        public final String source,name,phone,email;
        public ImportEntry(String source,String name,String phone,String email) {
            this.source=source;this.name=name;this.phone=phone;this.email=email;
        }
    }
    public static final class Result {
        public final int added,skipped;
        Result(int added,int skipped){this.added=added;this.skipped=skipped;}
    }
    private final File file;
    public ContactDirectory(WorkspaceStore workspace) {
        file=new File(workspace.root(),"master_data/contacts.csv");
    }
    private static List<String> row(String...fields){
        return new ArrayList<>(Arrays.asList(fields));
    }
    private static String clean(String text,int max){
        String value=text==null?"":text.trim();
        if(value.length()>max||value.indexOf('\0')>=0)
            throw new IllegalArgumentException("Invalid or oversized contact information");
        return value;
    }
    private static String phoneKey(String value){
        String digits=value.replaceAll("[^0-9]","");
        return digits.length()<7?"":digits;
    }
    private static String mailKey(String value){
        return value.toLowerCase(Locale.ROOT).trim();
    }
    private static String id(){return "CONT-"+UUID.randomUUID().toString().replace("-","");}
    private List<List<String>> read()throws IOException{
        if(!file.isFile()&&!new File(file.getPath()+".bak").isFile()){
            List<List<String>> empty=new ArrayList<>();
            empty.add(row(HEADER));write(empty);
        }
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        try(InputStream input=new AtomicFile(file).openRead()){
            byte[] buffer=new byte[8192];int got;
            while((got=input.read(buffer))!=-1){
                if(out.size()+got>16*1024*1024)
                    throw new IOException("Contact directory exceeds 16 MB; export/archive first");
                out.write(buffer,0,got);
            }
        }
        List<List<String>> rows=CsvCodec.read(out.toString("UTF-8"));
        if(rows.isEmpty()||!rows.get(0).equals(Arrays.asList(HEADER)))
            throw new IOException("Unrecognized contact directory version");
        for(List<String> r:rows)if(r.size()!=HEADER.length)
            throw new IOException("Malformed contact entry");
        return rows;
    }
    private void write(List<List<String>> rows)throws IOException {
        AtomicFile atomic=new AtomicFile(file);
        FileOutputStream out=null;
        try{
            out=atomic.startWrite();
            out.write(CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8));
            atomic.finishWrite(out);
        }catch(IOException|RuntimeException error){
            if(out!=null)atomic.failWrite(out);
            throw error;
        }
    }
    public synchronized List<Contact> all()throws IOException{
        List<List<String>> rows=read();
        List<Contact> result=new ArrayList<>();
        for(int i=1;i<rows.size();i++)result.add(new Contact(rows.get(i)));
        return result;
    }
    public synchronized Result importBatch(List<ImportEntry> items)throws IOException{
        if(items==null)throw new IllegalArgumentException("No contacts selected");
        List<List<String>> rows=read();
        Set<String> sources=new HashSet<>(),phones=new HashSet<>(),mails=new HashSet<>();
        for(int i=1;i<rows.size();i++){
            List<String> entry=rows.get(i);
            if(!entry.get(4).isEmpty())sources.add(entry.get(4));
            if(!phoneKey(entry.get(2)).isEmpty())phones.add(phoneKey(entry.get(2)));
            if(!entry.get(3).isEmpty())mails.add(mailKey(entry.get(3)));
        }
        int added=0,skipped=0;
        for(ImportEntry input:items){
            String source=clean(input.source,80),name=clean(input.name,180),
                phone=clean(input.phone,80),email=clean(input.email,160);
            String phoneId=phoneKey(phone),mailId=mailKey(email);
            if(name.isEmpty()||(source.length()>0&&sources.contains(source))||
                (!phoneId.isEmpty()&&phones.contains(phoneId))||
                (!mailId.isEmpty()&&mails.contains(mailId))){
                skipped++;continue;
            }
            rows.add(row(id(),name,phone,email,source,""));
            if(!source.isEmpty())sources.add(source);
            if(!phoneId.isEmpty())phones.add(phoneId);
            if(!mailId.isEmpty())mails.add(mailId);
            added++;
        }
        if(added>0)write(rows);
        return new Result(added,skipped);
    }
    public synchronized Contact add(String name,String phone,String email)throws IOException{
        Result r=importBatch(Collections.singletonList(new ImportEntry("",name,phone,email)));
        if(r.added==0)throw new IllegalArgumentException("Contact already exists");
        List<Contact> all=all();
        return all.get(all.size()-1);
    }
    public synchronized void update(String identifier,String name,String phone,String email)
        throws IOException{
        List<List<String>> rows=read();
        boolean found=false;
        for(int i=1;i<rows.size();i++){
            List<String> row=rows.get(i);
            if(row.get(0).equals(identifier)){
                row.set(1,clean(name,180));row.set(2,clean(phone,80));
                row.set(3,clean(email,160));
                if(row.get(1).isEmpty())throw new IllegalArgumentException("Name required");
                found=true;break;
            }
        }
        if(!found)throw new IOException("Contact not found");
        write(rows);
    }
    public synchronized void linkCustomer(String contactId,String customerId)throws IOException{
        if(!customerId.matches("CUST-[a-f0-9]{32}"))
            throw new IOException("Invalid customer ID");
        List<List<String>> rows=read();boolean found=false;
        for(int i=1;i<rows.size();i++)if(rows.get(i).get(0).equals(contactId)){
            rows.get(i).set(5,customerId);found=true;break;
        }
        if(!found)throw new IOException("Contact not found");
        write(rows);
    }
    public synchronized void delete(String contactId)throws IOException{
        List<List<String>> rows=read();
        boolean removed=rows.removeIf(r->r.get(0).equals(contactId));
        if(!removed)throw new IOException("Contact not found");
        write(rows);
    }
}
