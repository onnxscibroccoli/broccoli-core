package com.accubook.crm;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Bounded, user-initiated, on-device restore of Accubook's legacy CSV workspace.
 *
 * Stage -> validate -> rename prior root to rollback -> rename stage to live.
 * Both directory renames stay under one app-private parent. A crash between
 * renames is recovered on next startup. Previous snapshot is retained unless
 * the owner explicitly discards it. This is not multi-device synchronization.
 */
public final class BackupArchive {
    private BackupArchive() {}

    private static final long LIMIT_BYTES = 512L * 1024L * 1024L;
    private static final long LIMIT_PHOTO = 25L * 1024L * 1024L;
    private static final long LIMIT_OTHER = 16L * 1024L * 1024L;
    private static final int LIMIT_FILES = 10_000;

    private static final String[] CUSTOMER = {"CustomerID", "CompanyName", "ContactName",
        "Phone", "Email", "BillingStreet", "BillingCity", "BillingState", "BillingZip", "FolderPath"};
    private static final String[] JOB = {"JobID", "CustomerID", "JobTitle", "JobStreet",
        "JobCity", "JobState", "JobZip", "Status", "ScheduledDate", "TotalAmount"};
    private static final String[] ITEM = {"ItemID", "Description", "Quantity", "UnitRate", "LineTotal"};
    private static final String[] REQUEST = {"RequestID", "Description", "Quantity", "Unit", "Status"};
    private static final String[] CATALOG = {"ItemID", "Category", "ItemName", "DefaultUnit", "DefaultRate"};
    private static final String[] EXPENSE = {"ExpenseID", "Date", "Category", "Description", "Amount"};
    private static final String[] APPOINTMENT = {"StartTime","EndTime","Color","DaybookNote"};
    private static final String[] PREFS = {"Call","SMS","Email","Color"};
    private static final String[] QUOTE = {"QuoteSent","DateSent","QuoteNote"};
    private static final String[] PAYMENT = {"PaymentID","Date","Method","Amount","Reference","Notes"};
    private static final String[] ATTACHMENT = {"AttachmentID","DisplayName","MimeType","SizeBytes","StoredName"};
    private static final String[] BRAND = {"BusinessName","Address","Phone","Email","AccentColor","Terms","Footer","LogoMimeType"};
    private static final String[] MEMO = {"Greeting","Closing"};
    private static final String[] TIME = {"EntryID","Worker","StartedAt","EndedAt","Hours","Notes"};
    private static final String[] ROUTE = {"RecordedAt","Latitude","Longitude","AccuracyMeters"};


    public static File rollback(File live) {
        return new File(live.getParentFile(), live.getName() + ".previous");
    }

    private static File staging(File live) {
        return new File(live.getParentFile(), live.getName() + ".restore-staging");
    }

    /** Never create an empty workspace over a crashed restore. */
    public static void recover(File live) throws IOException {
        File previous = rollback(live);
        if (!live.exists() && previous.isDirectory()) {
            if (!previous.renameTo(live))
                throw new IOException("Restore interrupted; previous workspace cannot be reopened");
        } else if (!live.exists() && previous.exists()) {
            throw new IOException("Restore rollback is not a readable directory");
        }
    }

    private static void deleteTree(File root) throws IOException {
        if (!root.exists()) return;
        if (Files.isSymbolicLink(root.toPath())) throw new IOException("Refusing symbolic link");
        if (root.isDirectory()) {
            File[] children = root.listFiles();
            if (children == null) throw new IOException("Cannot inspect previous directory");
            for (File child : children) deleteTree(child);
        }
        if (!root.delete()) throw new IOException("Cannot remove " + root.getName());
    }

    private static String checked(String name) throws IOException {
        if (name == null || name.length() < 1 || name.length() > 512 ||
            name.startsWith("/") || name.indexOf('\\') >= 0 || name.indexOf(':') >= 0 ||
            name.indexOf((char) 0) >= 0) throw new IOException("Invalid ZIP entry name");
        for (String component : name.split("/", -1)) {
            if (component.isEmpty() || component.equals(".") || component.equals(".."))
                throw new IOException("Unsafe ZIP entry path");
        }
        return name;
    }

    private static boolean allowedFile(String name) {
        if (name.matches("master_data/(customers|jobs|catalog|expenses)\\.csv")) return true;
        if(name.equals("templates/branding.csv")||name.equals("templates/default_memo.csv")
            ||name.equals("templates/logo.bin"))return true;
        if (name.matches("templates/[A-Za-z0-9_./-]{1,220}\\.(html|txt|md|json)"))
            return !name.contains("..");
        String client = "customers/CUST-[a-f0-9]{32}_[A-Za-z0-9_-]{1,40}";
        if (name.matches(client + "/profile\\.md")) return true;
        if (name.matches(client + "/contact_preferences\\.csv")) return true;
        String job = client + "/jobs/JOB-[a-f0-9]{32}_[A-Za-z0-9_-]{1,40}";
        return name.matches(job + "/(job_items\\.csv|material_requests\\.csv|field_notes\\.md|job_details\\.json|"
            + "appointment\\.csv|quote\\.csv|payments\\.csv|invoice_memo\\.csv|"
            + "time_entries\\.csv|route_points\\.csv|"
            + "attachments\\.csv|attachments/ATT-[a-f0-9]{32}\\.bin|"
            + "photos/PHOTO-[a-f0-9]{32}\\.(jpg|png|webp))");
    }

    private static void unpack(File destination, InputStream input) throws IOException {
        byte[] buffer = new byte[8192];
        long total = 0;
        int entries = 0;
        Set<String> seen = new HashSet<>();
        try (ZipInputStream zip = new ZipInputStream(input, StandardCharsets.UTF_8)) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if (++entries > LIMIT_FILES) throw new IOException("ZIP has too many entries");
                String raw = entry.getName();
                // A directory may end in '/', but never allow traversal.
                String name = entry.isDirectory() && raw.endsWith("/")
                    ? raw.substring(0, raw.length() - 1) : raw;
                name = checked(name);
                if (entry.isDirectory()) {
                    zip.closeEntry();
                    continue;
                }
                if (!allowedFile(name)) throw new IOException("Unknown workspace file: " + name);
                if (!seen.add(name.toLowerCase(java.util.Locale.ROOT)))
                    throw new IOException("Duplicate ZIP path: " + name);
                File file = new File(destination, name).getCanonicalFile();
                if (!file.toPath().startsWith(destination.getCanonicalFile().toPath()))
                    throw new IOException("ZIP traversal blocked");
                File parent = file.getParentFile();
                if (!parent.isDirectory() && !parent.mkdirs())
                    throw new IOException("Cannot create staged folder");
                long written = 0;
                long perFile = name.equals("templates/logo.bin") ? 2L * 1024 * 1024
                    : (name.contains("/photos/") || name.contains("/attachments/"))
                        ? LIMIT_PHOTO : LIMIT_OTHER;
                try (FileOutputStream output = new FileOutputStream(file)) {
                    int count;
                    while ((count = zip.read(buffer)) != -1) {
                        written += count;
                        total += count;
                        if (written > perFile || total > LIMIT_BYTES)
                            throw new IOException("ZIP exceeds safe size limits");
                        output.write(buffer, 0, count);
                    }
                    output.getFD().sync();
                }
                zip.closeEntry(); // verifies CRC when present
            }
        }
    }

    private static List<List<String>> rows(File root, String path, String[] header)
        throws IOException {
        File file = new File(root, path);
        if (!file.isFile() || Files.isSymbolicLink(file.toPath()))
            throw new IOException("Missing workspace table: " + path);
        if (file.length() > LIMIT_OTHER)
            throw new IOException("Oversized table: " + path);
        byte[] bytes = Files.readAllBytes(file.toPath());
        String csv;
        try {
            csv = StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(java.nio.ByteBuffer.wrap(bytes)).toString();
        } catch (java.nio.charset.CharacterCodingException error) {
            throw new IOException("Table is not valid UTF-8: " + path, error);
        }
        List<List<String>> data = CsvCodec.read(csv);
        if (data.isEmpty() || !data.get(0).equals(Arrays.asList(header)))
            throw new IOException("Unexpected schema in " + path);
        for (List<String> row : data)
            if (row.size() != header.length)
                throw new IOException("Invalid row width in " + path);
        return data;
    }

    private static String slug(String value) {
        String safe = value.replaceAll("[^A-Za-z0-9_-]+", "_").replaceAll("_+", "_");
        if (safe.isEmpty() || safe.equals("_")) return "Record";
        return safe.length() > 40 ? safe.substring(0, 40) : safe;
    }

    /** Validate IDs, foreign keys, canonical billing rows and required files. */
    public static void validate(File root) throws IOException {
        if (!root.isDirectory() || Files.isSymbolicLink(root.toPath()))
            throw new IOException("Workspace root is missing or unsafe");
        List<List<String>> clients = rows(root, "master_data/customers.csv", CUSTOMER);
        List<List<String>> jobs = rows(root, "master_data/jobs.csv", JOB);
        rows(root, "master_data/catalog.csv", CATALOG);
        rows(root, "master_data/expenses.csv", EXPENSE);
        Map<String, String> folders = new HashMap<>();
        for (int i = 1; i < clients.size(); i++) {
            List<String> r = clients.get(i);
            String id = r.get(0), folder = r.get(9);
            if (!id.matches("CUST-[a-f0-9]{32}") ||
                !folder.matches("customers/" + id + "_[A-Za-z0-9_-]{1,40}") ||
                folders.put(id, folder) != null)
                throw new IOException("Invalid or duplicate customer ID/path");
            File path = new File(root, folder);
            if (!path.isDirectory() || Files.isSymbolicLink(path.toPath()))
                throw new IOException("Customer folder missing: " + id);
        }
        if(new File(root,"templates/default_memo.csv").isFile()){
            List<List<String>> templates=rows(root,"templates/default_memo.csv",MEMO);
            if(templates.size()>2)throw new IOException("Invalid default document template");
        }
        File branding=new File(root,"templates/branding.csv");
        if(branding.isFile()){
            List<List<String>> rows=rows(root,"templates/branding.csv",BRAND);
            if(rows.size()>2)throw new IOException("Multiple branding profiles");
            if(rows.size()==2){
                String mime=rows.get(1).get(7);
                if(!Arrays.asList("","image/png","image/jpeg","image/webp").contains(mime))
                    throw new IOException("Unsafe branding logo type");
                if(!mime.isEmpty()&&!new File(root,"templates/logo.bin").isFile())
                    throw new IOException("Branding logo missing");
            }
        }
        for(Map.Entry<String,String> client:folders.entrySet()){
            String name=client.getValue()+"/contact_preferences.csv";
            File file=new File(root,name);
            if(file.isFile()){
                List<List<String>> preferences=rows(root,name,PREFS);
                if(preferences.size()>2)throw new IOException("Repeated customer preferences");
                if(preferences.size()==2){
                    List<String> values=preferences.get(1);
                    for(int n=0;n<3;n++)
                        if(!values.get(n).equals("true")&&!values.get(n).equals("false"))
                            throw new IOException("Invalid preferred contact method");
                    if(!values.get(3).matches("#[0-9A-Fa-f]{6}"))
                        throw new IOException("Invalid customer color");
                }
            }
        }
        Set<String> jobIds = new HashSet<>();
        for (int i = 1; i < jobs.size(); i++) {
            List<String> r = jobs.get(i);
            String id = r.get(0), customer = r.get(1);
            if (!id.matches("JOB-[a-f0-9]{32}") || !jobIds.add(id) ||
                !folders.containsKey(customer))
                throw new IOException("Invalid or orphaned job ID");
            if (!Arrays.asList("Scheduled", "In Progress", "On Hold", "Completed", "Cancelled")
                .contains(r.get(7))) throw new IOException("Unknown job state");
            try { LocalDate.parse(r.get(8)); }
            catch (DateTimeParseException error) {
                throw new IOException("Malformed scheduled date", error);
            }
            String jobFolder = folders.get(customer) + "/jobs/" + id + "_" + slug(r.get(2));
            List<List<String>> details = rows(root, jobFolder + "/job_items.csv", ITEM);
            File requests = new File(root, jobFolder + "/material_requests.csv");
            if (requests.isFile()) {
                List<List<String>> materials = rows(root,
                    jobFolder + "/material_requests.csv", REQUEST);
                Set<String> requestIds = new HashSet<>();
                for (int n = 1; n < materials.size(); n++) {
                    List<String> material = materials.get(n);
                    if (!material.get(0).matches("REQ-[a-f0-9]{32}") ||
                        !requestIds.add(material.get(0)) ||
                        !Arrays.asList("Requested", "Ordered", "Delivered", "Used", "Cancelled")
                            .contains(material.get(4)))
                        throw new IOException("Invalid material request");
                    try {
                        BigDecimal quantity = new BigDecimal(material.get(2));
                        if (quantity.signum() <= 0 || quantity.scale() > 4 ||
                            quantity.compareTo(new BigDecimal("1000000")) > 0)
                            throw new IOException("Invalid requested quantity");
                    } catch (NumberFormatException error) {
                        throw new IOException("Invalid material quantity", error);
                    }
                }
            }
            File notes = new File(root, jobFolder + "/field_notes.md");
            if (notes.isFile()) {
                if (notes.length() > 64 * 1024)
                    throw new IOException("Oversized job notes");
                try {
                    StandardCharsets.UTF_8.newDecoder()
                        .onMalformedInput(CodingErrorAction.REPORT)
                        .decode(java.nio.ByteBuffer.wrap(Files.readAllBytes(notes.toPath())));
                } catch (java.nio.charset.CharacterCodingException error) {
                    throw new IOException("Job notes are invalid UTF-8", error);
                }
            }
            String appointmentPath=jobFolder+"/appointment.csv";
            if(new File(root,appointmentPath).isFile()){
                List<List<String>> appts=rows(root,appointmentPath,APPOINTMENT);
                if(appts.size()>2)throw new IOException("Multiple appointments for job");
                if(appts.size()==2){
                    List<String> detailsRow=appts.get(1);
                    try{
                        java.time.LocalTime from=java.time.LocalTime.parse(detailsRow.get(0));
                        java.time.LocalTime to=java.time.LocalTime.parse(detailsRow.get(1));
                        if(!to.isAfter(from))throw new IOException("Appointment end before start");
                    }catch(java.time.format.DateTimeParseException e){
                        throw new IOException("Invalid appointment time",e);
                    }
                    if(!detailsRow.get(2).matches("#[0-9A-Fa-f]{6}")||
                        detailsRow.get(3).length()>2000)
                        throw new IOException("Invalid appointment metadata");
                }
            }
            String quotePath=jobFolder+"/quote.csv";
            if(new File(root,quotePath).isFile()){
                List<List<String>> state=rows(root,quotePath,QUOTE);
                if(state.size()>2)throw new IOException("Repeated quote metadata");
                if(state.size()==2){
                    List<String> v=state.get(1);
                    if(!v.get(0).equals("true")&&!v.get(0).equals("false"))
                        throw new IOException("Invalid quote sent flag");
                    if(!v.get(1).isEmpty()){
                        try{LocalDate.parse(v.get(1));}
                        catch(DateTimeParseException e){throw new IOException("Invalid quote date",e);}
                    }
                }
            }
            String paymentsPath=jobFolder+"/payments.csv";
            if(new File(root,paymentsPath).isFile()){
                List<List<String>> ledger=rows(root,paymentsPath,PAYMENT);
                Set<String> ids=new HashSet<>();
                for(int k=1;k<ledger.size();k++){
                    List<String> value=ledger.get(k);
                    if(!value.get(0).matches("PAY-[a-f0-9]{32}")||
                        !ids.add(value.get(0))||
                        !Arrays.asList("Cash","Check","Cash App","PayPal","Bank Transfer","Other")
                            .contains(value.get(2)))
                        throw new IOException("Invalid payment identifier or method");
                    try{LocalDate.parse(value.get(1));}
                    catch(DateTimeParseException e){throw new IOException("Invalid payment date",e);}
                    try{
                        BigDecimal amount=new BigDecimal(value.get(3));
                        if(amount.signum()<=0||amount.scale()>2)
                            throw new IOException("Invalid payment amount");
                    }catch(NumberFormatException e){throw new IOException("Invalid payment amount",e);}
                }
            }
            String memoPath=jobFolder+"/invoice_memo.csv";
            if(new File(root,memoPath).isFile()){
                List<List<String>> memos=rows(root,memoPath,MEMO);
                if(memos.size()>2)throw new IOException("Invalid invoice layout metadata");
            }
            String timePath=jobFolder+"/time_entries.csv";
            if(new File(root,timePath).isFile()){
                List<List<String>> time=rows(root,timePath,TIME);
                Set<String> ids=new HashSet<>();
                for(int t=1;t<time.size();t++){
                    List<String> e=time.get(t);
                    if(!e.get(0).matches("TIME-[a-f0-9]{32}")||!ids.add(e.get(0))||
                        e.get(1).trim().isEmpty())throw new IOException("Invalid worker time entry");
                    try{
                        java.time.Instant from=java.time.Instant.parse(e.get(2));
                        if(!e.get(3).isEmpty()){
                            java.time.Instant to=java.time.Instant.parse(e.get(3));
                            if(!to.isAfter(from))throw new IOException("Negative elapsed time");
                            BigDecimal reported=new BigDecimal(e.get(4));
                            if(reported.signum()<0||reported.scale()>4)
                                throw new IOException("Invalid reported work hours");
                        }else if(!e.get(4).isEmpty())
                            throw new IOException("Running timer has a completed-hours value");
                    }catch(java.time.format.DateTimeParseException|NumberFormatException e){
                        throw new IOException("Invalid time record",e);
                    }
                }
            }
            String routePath=jobFolder+"/route_points.csv";
            if(new File(root,routePath).isFile()){
                List<List<String>> points=rows(root,routePath,ROUTE);
                if(points.size()>10002)throw new IOException("Oversized route");
                for(int p=1;p<points.size();p++){
                    List<String> v=points.get(p);
                    try{
                        java.time.Instant.parse(v.get(0));
                        double lat=Double.parseDouble(v.get(1));
                        double lon=Double.parseDouble(v.get(2));
                        double accuracy=Double.parseDouble(v.get(3));
                        if(!Double.isFinite(lat)||!Double.isFinite(lon)||
                            !Double.isFinite(accuracy)||lat< -90||lat>90||
                            lon< -180||lon>180||accuracy<0)
                            throw new IOException("Invalid recorded route point");
                    }catch(NumberFormatException|
                           java.time.format.DateTimeParseException e){
                        throw new IOException("Invalid route coordinate",e);
                    }
                }
            }
            String attachmentsPath=jobFolder+"/attachments.csv";
            if(new File(root,attachmentsPath).isFile()){
                List<List<String>> att=rows(root,attachmentsPath,ATTACHMENT);
                Set<String> ids=new HashSet<>();
                for(int k=1;k<att.size();k++){
                    List<String> entry=att.get(k);
                    String identifier=entry.get(0), name=entry.get(4);
                    if(!identifier.matches("ATT-[a-f0-9]{32}")||
                        !name.equals(identifier+".bin")||!ids.add(identifier))
                        throw new IOException("Unsafe or repeated attachment ID");
                    File binary=new File(root,jobFolder+"/attachments/"+name);
                    if(!binary.isFile()||Files.isSymbolicLink(binary.toPath()))
                        throw new IOException("Attachment binary is missing");
                    try{
                        if(Long.parseLong(entry.get(3))!=binary.length()||
                            binary.length()>LIMIT_PHOTO)
                            throw new IOException("Attachment byte count mismatch");
                    }catch(NumberFormatException e){throw new IOException("Invalid attachment size",e);}
                }
            }
            BigDecimal sum = BigDecimal.ZERO;
            for (int n = 1; n < details.size(); n++) {
                List<String> line = details.get(n);
                try {
                    BigDecimal expected = new BigDecimal(line.get(2))
                        .multiply(new BigDecimal(line.get(3))).setScale(2, RoundingMode.HALF_UP);
                    BigDecimal recorded = new BigDecimal(line.get(4));
                    if (expected.compareTo(recorded) != 0)
                        throw new IOException("Incorrect line total on job " + id);
                    sum = sum.add(recorded);
                } catch (NumberFormatException | ArithmeticException error) {
                    throw new IOException("Invalid billing amount on job " + id, error);
                }
            }
            try {
                if (sum.compareTo(new BigDecimal(r.get(9))) != 0)
                    throw new IOException("Job total disagrees with canonical lines: " + id);
            } catch (NumberFormatException error) {
                throw new IOException("Invalid cached job total", error);
            }
        }
    }

    /** Replace current workspace only after fully validating the selected ZIP. */
    public static void restore(File live, InputStream source) throws IOException {
        if (source == null) throw new IOException("Cannot read selected ZIP backup");
        recover(live);
        File previous = rollback(live);
        File temp = staging(live);
        if (previous.exists()) {
            throw new IOException("A previous restore snapshot exists. Verify the live data "
                + "and explicitly discard that snapshot before restoring again.");
        }
        deleteTree(temp); // only an incomplete staging copy; never the live workspace
        if (!temp.mkdirs()) throw new IOException("Cannot stage ZIP restore");
        boolean staged = true;
        try {
            unpack(temp, source);
            validate(temp);
            if (live.exists() && !live.renameTo(previous))
                throw new IOException("Cannot preserve current workspace for rollback");
            if (!temp.renameTo(live)) {
                if (previous.exists() && !previous.renameTo(live))
                    throw new IOException("Restore interrupted: rollback failed; preserve files");
                throw new IOException("Cannot activate validated restore");
            }
            staged = false;
        } finally {
            if (staged) {
                // If swap/rollback failed, preserve files rather than deleting evidence.
                if (!previous.exists() || live.exists()) deleteTree(temp);
            }
        }
    }

    /** Revert to the previously retained workspace; preserve failed live data for inspection. */
    public static void revertPreviousSnapshot(File live) throws IOException {
        File old = rollback(live);
        validate(old);
        File failed = new File(live.getParentFile(), live.getName() + ".failed-live");
        if (failed.exists()) throw new IOException("A failed-live snapshot already exists; "
            + "preserve and inspect it before attempting another rollback");
        if (live.exists() && !live.renameTo(failed))
            throw new IOException("Cannot preserve current workspace before rollback");
        if (!old.renameTo(live)) {
            if (failed.exists() && !failed.renameTo(live))
                throw new IOException("Could not activate rollback; both copies preserved");
            throw new IOException("Unable to reopen previous workspace");
        }
    }

    /** Explicitly remove the one previous snapshot, never the current workspace. */
    public static void clearPreviousSnapshot(File live) throws IOException {
        validate(live);
        deleteTree(rollback(live));
    }
}
