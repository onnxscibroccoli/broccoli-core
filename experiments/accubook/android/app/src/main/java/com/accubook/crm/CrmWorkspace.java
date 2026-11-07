package com.accubook.crm;

import android.util.AtomicFile;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

/**
 * Opt-in offline CRM extensions. Stable IDs; additive CSV files; no network APIs.
 * Transactions are atomic per file. App-level multi-file commit is not yet guaranteed.
 */
public final class CrmWorkspace {
    private final WorkspaceStore workspace;
    private final File root;
    private static final String[] APPOINTMENT = {"StartTime","EndTime","Color","DaybookNote"};
    private static final String[] PREFERENCES = {"Call","SMS","Email","Color"};
    private static final String[] QUOTE = {"QuoteSent","DateSent","QuoteNote"};
    private static final String[] PAYMENTS = {"PaymentID","Date","Method","Amount","Reference","Notes"};
    private static final String[] ATTACHMENTS = {"AttachmentID","DisplayName","MimeType","SizeBytes","StoredName"};
    private static final String[] BRANDING = {"BusinessName","Address","Phone","Email","AccentColor","Terms","Footer","LogoMimeType"};
    private static final String[] MEMO = {"Greeting","Closing"};
    public static final String[] PAYMENT_METHODS = {"Cash", "Check", "Cash App", "PayPal", "Bank Transfer", "Other"};
    public static final String[] JOB_COLORS = {"#165DAB","#137C66","#A16B0B","#A33F49","#7655A4","#4E6476"};

    public static final class Appointment {
        public final String start, end, color, notes;
        Appointment(List<String> row) { start=row.get(0); end=row.get(1); color=row.get(2); notes=row.get(3); }
    }
    public static final class ContactPreferences {
        public final boolean call, sms, email;
        public final String color;
        ContactPreferences(List<String> row) {
            call=Boolean.parseBoolean(row.get(0)); sms=Boolean.parseBoolean(row.get(1));
            email=Boolean.parseBoolean(row.get(2)); color=row.get(3);
        }
    }
    public static final class Quote {
        public final boolean sent;
        public final String sentDate, note;
        Quote(List<String> row) { sent=Boolean.parseBoolean(row.get(0)); sentDate=row.get(1); note=row.get(2); }
    }
    public static final class Payment {
        public final String id, date, method, amount, reference, note;
        Payment(List<String> row) {
            id=row.get(0);date=row.get(1);method=row.get(2);amount=row.get(3);
            reference=row.get(4);note=row.get(5);
        }
    }
    public static final class Attachment {
        public final String id, name, mime, bytes, stored;
        Attachment(List<String> row) {
            id=row.get(0); name=row.get(1); mime=row.get(2); bytes=row.get(3); stored=row.get(4);
        }
    }
    public static final class Branding {
        public final String business, address, phone, email, accent, terms, footer, logoMime;
        Branding(List<String> r) {
            business=r.get(0);address=r.get(1);phone=r.get(2);email=r.get(3);
            accent=r.get(4);terms=r.get(5);footer=r.get(6);logoMime=r.get(7);
        }
    }
    public static final class Memo {
        public final String greeting, closing;
        Memo(List<String> r) { greeting=r.get(0); closing=r.get(1); }
    }

    public CrmWorkspace(WorkspaceStore store) {
        workspace = store;
        root = store.root();
    }

    private static List<String> row(String... fields) {
        return new ArrayList<>(Arrays.asList(fields));
    }
    private static List<List<String>> one(String[] header, String... values) {
        List<List<String>> result = new ArrayList<>();
        result.add(row(header));
        if (values != null && values.length != 0) result.add(row(values));
        return result;
    }
    private static File directory(File folder) throws IOException {
        if (!folder.isDirectory() && !folder.mkdirs()) throw new IOException("Cannot create workspace folder");
        return folder;
    }
    private static byte[] read(File file, long max) throws IOException {
        AtomicFile atomic = new AtomicFile(file);
        try (InputStream input = atomic.openRead(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[8192];
            int got;
            while ((got=input.read(buf)) != -1) {
                if (out.size() + (long)got > max) throw new IOException("Workspace file too large");
                out.write(buf,0,got);
            }
            return out.toByteArray();
        }
    }
    private static void write(File file, byte[] bytes) throws IOException {
        AtomicFile atomic = new AtomicFile(file);
        FileOutputStream out = null;
        try {
            out = atomic.startWrite();
            out.write(bytes);
            atomic.finishWrite(out);
        } catch (IOException | RuntimeException error) {
            if (out!=null) atomic.failWrite(out);
            throw error;
        }
    }
    private static void writeTable(File file,List<List<String>> rows) throws IOException {
        write(file,CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8));
    }
    private static List<List<String>> table(File file, String[] header) throws IOException {
        if (!file.isFile() && !new File(file.getPath()+".bak").isFile())
            writeTable(file,one(header));
        List<List<String>> r = CsvCodec.read(new String(read(file,4L*1024*1024),StandardCharsets.UTF_8));
        if (r.isEmpty() || !r.get(0).equals(Arrays.asList(header)))
            throw new IOException("Unexpected CSV schema: " + file.getName());
        for (List<String> line:r) if(line.size()!=header.length)
            throw new IOException("Invalid data row: " +file.getName());
        return r;
    }
    private static String text(String input, int max, boolean required) {
        String value=input==null?"":input.trim();
        if(required && value.isEmpty())throw new IllegalArgumentException("Required entry is empty");
        if(value.length()>max || value.indexOf((char)0)>=0)throw new IllegalArgumentException("Text too long or invalid");
        return value;
    }
    private static String color(String input) {
        String value=text(input,7,true).toUpperCase(Locale.ROOT);
        if(!value.matches("#[0-9A-F]{6}"))throw new IllegalArgumentException("Invalid color");
        return value;
    }
    private static String hour(String input) {
        String value=text(input,5,true);
        try {LocalTime.parse(value);} catch(Exception e) {throw new IllegalArgumentException("Time must be HH:mm");}
        if(!value.matches("[0-2][0-9]:[0-5][0-9]"))throw new IllegalArgumentException("Time must be HH:mm");
        return value;
    }
    private static String date(String input) {
        String value=text(input,10,true);
        try {LocalDate.parse(value);} catch(Exception e) {throw new IllegalArgumentException("Date must be YYYY-MM-DD");}
        return value;
    }
    private static File safeChild(File base,String relative) throws IOException {
        File file=new File(base,relative).getCanonicalFile();
        if(!file.toPath().startsWith(base.getCanonicalFile().toPath()) || file.equals(base))
            throw new IOException("Unsafe workspace path");
        return file;
    }
    private static String slug(String value) {
        String safe=value.replaceAll("[^A-Za-z0-9_-]+","_").replaceAll("_+","_");
        if(safe.isEmpty()||safe.equals("_"))return "Record";
        return safe.length()>40?safe.substring(0,40):safe;
    }
    private File customerDir(WorkspaceStore.Customer customer) throws IOException {
        boolean found=false;
        for(WorkspaceStore.Customer c:workspace.customers())
            if(c.id.equals(customer.id) && c.folder.equals(customer.folder))found=true;
        if(!found || !customer.folder.matches("customers/CUST-[a-f0-9]{32}_[A-Za-z0-9_-]{1,40}"))
            throw new IOException("Unknown customer");
        return safeChild(root,customer.folder);
    }
    private File jobDir(WorkspaceStore.Job job) throws IOException {
        WorkspaceStore.Customer customer=null;
        for(WorkspaceStore.Customer c:workspace.customers())
            if(c.id.equals(job.customerId))customer=c;
        if(customer==null) throw new IOException("Job has no customer");
        boolean found=false;
        for(WorkspaceStore.Job j:workspace.jobs())
            if(j.id.equals(job.id)&&j.customerId.equals(job.customerId)&&j.title.equals(job.title))found=true;
        if(!found || !job.id.matches("JOB-[a-f0-9]{32}"))throw new IOException("Job not found");
        return safeChild(customerDir(customer),"jobs/"+job.id+"_"+slug(job.title));
    }
    private File global(String relative) throws IOException {
        return safeChild(root,relative);
    }

    public synchronized Appointment appointment(WorkspaceStore.Job job) throws IOException {
        List<List<String>> r=table(new File(jobDir(job),"appointment.csv"),APPOINTMENT);
        if(r.size()==1)return new Appointment(row("09:00","10:00",JOB_COLORS[0],""));
        return new Appointment(r.get(1));
    }
    public synchronized void saveAppointment(WorkspaceStore.Job job,String start,String end,
                                             String tint,String note) throws IOException {
        String from=hour(start), to=hour(end);
        if(!LocalTime.parse(to).isAfter(LocalTime.parse(from)))
            throw new IllegalArgumentException("End time must follow start time");
        File file=new File(jobDir(job),"appointment.csv");
        writeTable(file,one(APPOINTMENT,from,to,color(tint),text(note,2000,false)));
    }
    public synchronized ContactPreferences preferences(WorkspaceStore.Customer customer) throws IOException {
        List<List<String>> r=table(new File(customerDir(customer),"contact_preferences.csv"),PREFERENCES);
        if(r.size()==1)return new ContactPreferences(row("true","false",
            customer.email.isEmpty()?"false":"true",JOB_COLORS[0]));
        return new ContactPreferences(r.get(1));
    }
    public synchronized void savePreferences(WorkspaceStore.Customer customer,boolean call,
                                             boolean sms, boolean email,String tint) throws IOException {
        if(!call&&!sms&&!email) throw new IllegalArgumentException("Select at least one preferred contact method");
        writeTable(new File(customerDir(customer),"contact_preferences.csv"),
            one(PREFERENCES,Boolean.toString(call),Boolean.toString(sms),
                Boolean.toString(email),color(tint)));
    }
    public synchronized Quote quote(WorkspaceStore.Job job) throws IOException {
        List<List<String>> r=table(new File(jobDir(job),"quote.csv"),QUOTE);
        return r.size()==1?new Quote(row("false","","")):new Quote(r.get(1));
    }
    public synchronized void setQuoteSent(WorkspaceStore.Job job,boolean sent,String note) throws IOException {
        writeTable(new File(jobDir(job),"quote.csv"),
            one(QUOTE,Boolean.toString(sent),sent?LocalDate.now().toString():"",
                text(note,1000,false)));
    }
    public synchronized List<Payment> payments(WorkspaceStore.Job job) throws IOException {
        List<List<String>> r=table(new File(jobDir(job),"payments.csv"),PAYMENTS);
        List<Payment> values=new ArrayList<>();
        for(int i=1;i<r.size();i++)values.add(new Payment(r.get(i)));
        return values;
    }
    public static BigDecimal money(String value,boolean positive) {
        BigDecimal n;
        try {n=new BigDecimal(value.trim());}
        catch(Exception e){throw new IllegalArgumentException("Enter a valid monetary amount");}
        if(n.scale()>2 || n.abs().compareTo(new BigDecimal("9999999.99"))>0 ||
            (positive&&n.signum()<=0)) throw new IllegalArgumentException("Amount must be positive with 0–2 decimal places");
        return n.setScale(2,RoundingMode.UNNECESSARY);
    }
    public synchronized Payment addPayment(WorkspaceStore.Job job,String when,String method,
                                          String amount,String reference,String notes) throws IOException {
        date(when);
        if(!Arrays.asList(PAYMENT_METHODS).contains(method))throw new IllegalArgumentException("Select payment method");
        String sum=money(amount,true).toPlainString();
        List<String> value=row("PAY-"+UUID.randomUUID().toString().replace("-",""),
            when,method,sum,text(reference,160,false),text(notes,500,false));
        File file=new File(jobDir(job),"payments.csv");
        List<List<String>> rows=table(file,PAYMENTS);
        rows.add(value);
        writeTable(file,rows);
        return new Payment(value);
    }
    public synchronized BigDecimal received(WorkspaceStore.Job job) throws IOException {
        BigDecimal total=BigDecimal.ZERO;
        for(Payment p:payments(job))total=total.add(new BigDecimal(p.amount));
        return total;
    }
    public synchronized BigDecimal balance(WorkspaceStore.Job job) throws IOException {
        return new BigDecimal(job.total).subtract(received(job));
    }

    private File attachmentDirectory(WorkspaceStore.Job job) throws IOException {
        return directory(new File(jobDir(job),"attachments"));
    }
    private File attachmentIndex(WorkspaceStore.Job job) throws IOException {
        return new File(jobDir(job),"attachments.csv");
    }
    public synchronized List<Attachment> attachments(WorkspaceStore.Job job) throws IOException {
        List<List<String>> rows=table(attachmentIndex(job),ATTACHMENTS);
        List<Attachment> list=new ArrayList<>();
        for(int i=1;i<rows.size();i++)list.add(new Attachment(rows.get(i)));
        return list;
    }
    /** Store any MIME type, never execute/open untrusted bytes inside Accubook. */
    public synchronized Attachment importAttachment(WorkspaceStore.Job job,InputStream stream,
                                                    String displayName,String mime) throws IOException {
        if(stream==null)throw new IOException("Cannot open selected file");
        String name=text(displayName,180,true),type=text(mime,120,false);
        if(type.isEmpty())type="application/octet-stream";
        String identifier="ATT-"+UUID.randomUUID().toString().replace("-","");
        File output=new File(attachmentDirectory(job),identifier+".bin");
        AtomicFile atomic=new AtomicFile(output);
        FileOutputStream dest=null;
        long count=0;
        try {
            dest=atomic.startWrite();
            byte[] buffer=new byte[8192];
            int n;
            while((n=stream.read(buffer))!=-1) {
                count+=n;
                if(count>25L*1024*1024)throw new IOException("Individual attachment exceeds 25 MB");
                dest.write(buffer,0,n);
            }
            atomic.finishWrite(dest);
        }catch(IOException|RuntimeException e){
            if(dest!=null)atomic.failWrite(dest);
            throw e;
        }
        List<String> value=row(identifier,name,type,Long.toString(count),identifier+".bin");
        File index=attachmentIndex(job);
        List<List<String>> rows=table(index,ATTACHMENTS);
        rows.add(value);
        try{writeTable(index,rows);}
        catch(IOException e){if(!output.delete())e.addSuppressed(new IOException("Orphan attachment pending cleanup")); throw e;}
        return new Attachment(value);
    }
    public synchronized File fileFor(WorkspaceStore.Job job, Attachment attachment) throws IOException {
        boolean found=false;
        for(Attachment candidate:attachments(job))
            if(candidate.id.equals(attachment.id)&&candidate.stored.equals(attachment.stored))found=true;
        if(!found||!attachment.stored.matches("ATT-[a-f0-9]{32}\\.bin"))
            throw new IOException("Attachment not found");
        File file=new File(attachmentDirectory(job),attachment.stored);
        if(!file.isFile()||java.nio.file.Files.isSymbolicLink(file.toPath()))throw new IOException("Attachment missing");
        return file;
    }
    public synchronized void deleteAttachment(WorkspaceStore.Job job,Attachment attachment) throws IOException {
        File binary=fileFor(job,attachment);
        File index=attachmentIndex(job);
        List<List<String>> rows=table(index,ATTACHMENTS);
        boolean changed=rows.removeIf(r->r.get(0).equals(attachment.id));
        if(!changed)throw new IOException("Attachment not found");
        // Move bytes out of index reach first; no destructive deletion until index is durable.
        writeTable(index,rows);
        if(!binary.delete())throw new IOException("Attachment unlinked but file cleanup incomplete");
    }

    private File brandingFile() throws IOException {return global("templates/branding.csv");}
    public synchronized Branding branding() throws IOException {
        List<List<String>> rows=table(brandingFile(),BRANDING);
        if(rows.size()==1)return new Branding(row("My Business","","","","#165DAB",
            "Payment due on receipt.","Thank you for your business.",""));
        return new Branding(rows.get(1));
    }
    public synchronized void saveBranding(String business,String address,String phone,String email,
                                         String accent,String terms,String footer) throws IOException {
        Branding prior=branding();
        List<String> r=row(text(business,120,true),text(address,250,false),
            text(phone,80,false),text(email,120,false),color(accent),
            text(terms,1500,false),text(footer,1500,false),prior.logoMime);
        writeTable(brandingFile(),one(BRANDING,r.toArray(new String[0])));
    }
    public synchronized void saveLogo(InputStream source,String mime) throws IOException {
        if(source==null||!Arrays.asList("image/png","image/jpeg","image/webp").contains(mime))
            throw new IllegalArgumentException("Choose PNG, JPEG or WebP logo");
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        byte[] buffer=new byte[4096];int n;
        while((n=source.read(buffer))!=-1){
            if(bytes.size()+n>2*1024*1024)throw new IOException("Logo must be <= 2MB");
            bytes.write(buffer,0,n);
        }
        Branding old=branding();
        write(global("templates/logo.bin"),bytes.toByteArray());
        writeTable(brandingFile(),one(BRANDING,old.business,old.address,old.phone,old.email,
            old.accent,old.terms,old.footer,mime));
    }
    public synchronized byte[] logo() throws IOException {
        Branding brand=branding();
        File file=global("templates/logo.bin");
        return brand.logoMime.isEmpty()||!file.isFile()?new byte[0]:read(file,2L*1024*1024);
    }
    public synchronized Memo defaultMemo() throws IOException {
        List<List<String>> r=table(global("templates/default_memo.csv"),MEMO);
        return r.size()==1?new Memo(row("Thank you for choosing us.","")):new Memo(r.get(1));
    }
    public synchronized void saveDefaultMemo(String greeting,String closing) throws IOException {
        writeTable(global("templates/default_memo.csv"),
            one(MEMO,text(greeting,1800,false),text(closing,1800,false)));
    }
    public synchronized Memo memo(WorkspaceStore.Job job) throws IOException {
        List<List<String>> r=table(new File(jobDir(job),"invoice_memo.csv"),MEMO);
        return r.size()==1?defaultMemo():new Memo(r.get(1));
    }
    public synchronized void saveMemo(WorkspaceStore.Job job,String greeting,String closing) throws IOException {
        writeTable(new File(jobDir(job),"invoice_memo.csv"),
            one(MEMO,text(greeting,1800,false),text(closing,1800,false)));
    }
}
