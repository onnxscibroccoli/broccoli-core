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
    private static final String[] EXPENSES = {"ExpenseID","Date","Category","Description","Amount"};
    private static final String[] TIME_ENTRIES = {"EntryID","Worker","StartedAt","EndedAt","Hours","Notes"};
    private static final String[] ROUTE = {"RecordedAt","Latitude","Longitude","AccuracyMeters"};

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
    public static final class Expense {
        public final String id,date,category,description,amount;
        Expense(List<String> r) {
            id=r.get(0);date=r.get(1);category=r.get(2);
            description=r.get(3);amount=r.get(4);
        }
    }
    public static final class TimeEntry {
        public final String id,worker,start,end,hours,note;
        TimeEntry(List<String> r) {
            id=r.get(0);worker=r.get(1);start=r.get(2);end=r.get(3);
            hours=r.get(4);note=r.get(5);
        }
        public boolean active(){return end.isEmpty();}
    }
    public static final class RoutePoint {
        public final String at,latitude,longitude,accuracy;
        RoutePoint(List<String> r){
            at=r.get(0);latitude=r.get(1);longitude=r.get(2);accuracy=r.get(3);
        }
    }
    public static final class Branding {
        public final String business, address, phone, email, accent, terms, footer, logoMime;
        Branding(List<String> r) {
            business=r.get(0);address=r.get(1);phone=r.get(2);email=r.get(3);
            accent=r.get(4);terms=r.get(5);footer=r.get(6);logoMime=r.get(7);
        }
        Branding withLogoMime(String mime) {
            return new Branding(java.util.Arrays.asList(business,address,phone,email,
                accent,terms,footer,mime));
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

    /** Manual offline costs. Never equate an expense with a bank-cleared payment. */
    public synchronized List<Expense> expenses() throws IOException {
        List<List<String>> rows=table(global("master_data/expenses.csv"),EXPENSES);
        List<Expense> result=new ArrayList<>();
        for(int i=1;i<rows.size();i++)result.add(new Expense(rows.get(i)));
        return result;
    }
    public synchronized Expense addExpense(String when,String category,String description,
                                          String amount) throws IOException {
        List<String> r=row("EXP-"+UUID.randomUUID().toString().replace("-",""),
            date(when),text(category,100,true),text(description,250,true),
            money(amount,true).toPlainString());
        File path=global("master_data/expenses.csv");
        List<List<String>> rows=table(path,EXPENSES);
        rows.add(r);writeTable(path,rows);
        return new Expense(r);
    }
    public synchronized void deleteExpense(String identifier) throws IOException {
        File path=global("master_data/expenses.csv");
        List<List<String>> rows=table(path,EXPENSES);
        boolean removed=rows.removeIf(r->r.get(0).equals(identifier));
        if(!removed)throw new IOException("Expense not found");
        writeTable(path,rows);
    }

    /** One device may register multiple named workers, each with a separate timer. */
    public synchronized List<TimeEntry> timeEntries(WorkspaceStore.Job job) throws IOException {
        List<List<String>> rows=table(new File(jobDir(job),"time_entries.csv"),TIME_ENTRIES);
        List<TimeEntry> entries=new ArrayList<>();
        for(int i=1;i<rows.size();i++)entries.add(new TimeEntry(rows.get(i)));
        return entries;
    }
    public synchronized TimeEntry clockIn(WorkspaceStore.Job job,String worker,String note)
        throws IOException {
        String name=text(worker,100,true);
        for(TimeEntry existing:timeEntries(job))
            if(existing.active()&&existing.worker.equalsIgnoreCase(name))
                throw new IllegalArgumentException("This worker is already clocked in");
        List<String> r=row("TIME-"+UUID.randomUUID().toString().replace("-",""),name,
            java.time.Instant.now().toString(),"","",text(note,1000,false));
        File path=new File(jobDir(job),"time_entries.csv");
        List<List<String>> rows=table(path,TIME_ENTRIES);
        rows.add(r);writeTable(path,rows);
        return new TimeEntry(r);
    }
    public synchronized TimeEntry clockOut(WorkspaceStore.Job job,String id) throws IOException {
        File path=new File(jobDir(job),"time_entries.csv");
        List<List<String>> rows=table(path,TIME_ENTRIES);
        for(int i=1;i<rows.size();i++){
            List<String> record=rows.get(i);
            if(record.get(0).equals(id)&&record.get(3).isEmpty()){
                java.time.Instant start=java.time.Instant.parse(record.get(2));
                java.time.Instant end=java.time.Instant.now();
                if(!end.isAfter(start))throw new IOException("Clock time moved backward");
                BigDecimal hours=BigDecimal.valueOf(java.time.Duration.between(start,end)
                    .toMillis()).divide(new BigDecimal("3600000"),4,RoundingMode.HALF_UP);
                record.set(3,end.toString());
                record.set(4,hours.toPlainString());
                writeTable(path,rows);
                return new TimeEntry(record);
            }
        }
        throw new IOException("Active timer not found; no changes saved");
    }
    public synchronized BigDecimal totalHours(WorkspaceStore.Job job) throws IOException {
        BigDecimal total=BigDecimal.ZERO;
        for(TimeEntry entry:timeEntries(job))
            if(!entry.hours.isEmpty())total=total.add(new BigDecimal(entry.hours));
        return total;
    }
    /** Route coordinates are recorded only after explicit opt-in, locally. */
    public synchronized void recordLocation(WorkspaceStore.Job job,double lat,double lon,
                                            float accuracy) throws IOException {
        if(!Double.isFinite(lat)||!Double.isFinite(lon)||lat< -90||lat>90||
            lon< -180||lon>180||!Float.isFinite(accuracy)||accuracy<0)
            throw new IllegalArgumentException("Invalid location point");
        File path=new File(jobDir(job),"route_points.csv");
        List<List<String>> rows=table(path,ROUTE);
        if(rows.size()>10001)throw new IOException("Route point limit reached");
        rows.add(row(java.time.Instant.now().toString(),
            Double.toString(lat),Double.toString(lon),Float.toString(accuracy)));
        writeTable(path,rows);
    }
    public synchronized List<RoutePoint> routePoints(WorkspaceStore.Job job) throws IOException {
        List<List<String>> rows=table(new File(jobDir(job),"route_points.csv"),ROUTE);
        List<RoutePoint> result=new ArrayList<>();
        for(int i=1;i<rows.size();i++)result.add(new RoutePoint(rows.get(i)));
        return result;
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
        if(rows.size()==1)return new Branding(row("Jules Gutter Cleaning",
            "15 Ward Street, Hingham, MA 02043","267-667-2321",
            "julesguttercleaning@gmail.com","#165DAB",
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
