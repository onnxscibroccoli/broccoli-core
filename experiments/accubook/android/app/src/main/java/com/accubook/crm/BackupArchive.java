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
    private static final String[] PRICEBOOK={
        "CatalogID","Category","Name","Unit","BaseCost","MarkupPercent","Supplier","UpdatedUTC"};
    private static final String[] MILESTONE={"Key","Name","Complete","CompletedUTC","Notes"};
    private static final String[] LOGISTICS={
        "Vendor","MaterialDeliveryContact","AssignedCrew","OperationsNotes"};
    private static final String[] PICKUP={"DueAtUTC","ConfiguredAtUTC","State"};
    private static final String[] CONTACTS={"ContactID","Name","Phone","Email","SourceID","CustomerID"};
    private static final String[] JOB_MASTER={"FieldID","Label","Kind","Required","DefaultValue","Active"};
    private static final String[] JOB_FIELD={"FieldID","Label","Kind","Required","Value","Active","Origin"};
    private static final String[] PHOTO_ORDER={"PhotoFile","Position"};
    private static final String[] CHANGE_ORDERS={"ChangeOrderID","Title","Status",
        "CreatedUTC","AcknowledgedUTC","SignedBy","SignatureSHA256","ContentSHA256"};
    private static final String[] CHANGE_ORDER_LINES={"LineID","ChangeOrderID",
        "Description","Quantity","UnitRate","Amount"};
    private static final String[] SERVICE_INTERVALS={
        "ScheduleID","CustomerID","SourceJobID","ServiceLabel","SiteName",
        "LastServiceDate","IntervalMonths","LastMileage","IntervalMiles",
        "DueDate","DueMileage","Active"};


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
        if (name.matches("master_data/(customers|jobs|catalog|expenses|pricebook|calendar_links|contacts|service_intervals)\\.csv")) return true;
        if(name.equals("templates/branding.csv")||name.equals("templates/business_setup.csv")
            ||name.equals("templates/job_fields.csv")
            ||name.equals("templates/default_memo.csv")
            ||name.equals("templates/logo.bin"))return true;
        if (name.matches("templates/[A-Za-z0-9_./-]{1,220}\\.(html|txt|md|json)"))
            return !name.contains("..");
        String client = "customers/CUST-[a-f0-9]{32}_[A-Za-z0-9_-]{1,40}";
        if (name.matches(client + "/profile\\.md")) return true;
        if (name.matches(client + "/contact_preferences\\.csv")) return true;
        String job = client + "/jobs/JOB-[a-f0-9]{32}_[A-Za-z0-9_-]{1,40}";
        return name.matches(job + "/(job_items\\.csv|material_requests\\.csv|field_notes\\.md|job_details\\.json|"
            + "appointment\\.csv|quote\\.csv|payments\\.csv|invoice_memo\\.csv|"
            + "time_entries\\.csv|route_points\\.csv|job_milestones\\.csv|"
            + "job_logistics\\.csv|pickup_reminder\\.csv|custom_fields\\.csv|photo_order\\.csv|"
            + "change_orders\\.csv|change_order_lines\\.csv|"
            + "change_order_signatures/CO-[a-f0-9]{32}\\.png|"
            + "attachments\\.csv|attachments/ATT-[a-f0-9]{32}\\.bin|"
            + "photos/PHOTO-[a-f0-9]{32}\\.(jpg|png|webp|heic|heif|avif|gif|bmp|tiff|dng|img))");
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

    private static void verifyFlexibleFields(List<List<String>> rows,boolean job)
        throws IOException {
        Set<String> ids=new HashSet<>();
        for(int i=1;i<rows.size();i++){
            List<String> r=rows.get(i);
            if(!r.get(0).matches("FIELD-[a-f0-9]{32}")||!ids.add(r.get(0))||
               r.get(1).trim().isEmpty()||r.get(1).length()>120||
               !Arrays.asList("Checkbox","Text","Date","Number").contains(r.get(2))||
               !Arrays.asList("true","false").contains(r.get(3))||
               !Arrays.asList("true","false").contains(r.get(5))||
               r.get(4).length()>2000||
               (job&&!Arrays.asList("Master","Job").contains(r.get(6))))
                throw new IOException("Invalid custom field");
            if(r.get(2).equals("Checkbox")&&!Arrays.asList("true","false").contains(r.get(4)))
                throw new IOException("Invalid custom checkbox value");
            if(r.get(2).equals("Date")&&!r.get(4).isEmpty())
                try{LocalDate.parse(r.get(4));}
                catch(DateTimeParseException e){throw new IOException("Invalid custom date",e);}
            if(r.get(2).equals("Number")&&!r.get(4).isEmpty())
                try{new BigDecimal(r.get(4));}
                catch(NumberFormatException e){throw new IOException("Invalid custom number",e);}
        }
    }


    private static void validateChangeOrders(File root,String folder,String jobId)
        throws IOException {
        File index=new File(root,folder+"/change_orders.csv");
        File lineFile=new File(root,folder+"/change_order_lines.csv");
        if(!index.isFile()&&!lineFile.isFile())return; // Older workspace.
        if(!index.isFile()||!lineFile.isFile())
            throw new IOException("Incomplete change-order tables");
        List<List<String>> orders=rows(root,folder+"/change_orders.csv",CHANGE_ORDERS);
        List<List<String>> lines=rows(root,folder+"/change_order_lines.csv",CHANGE_ORDER_LINES);
        if(orders.size()>1001||lines.size()>1001)
            throw new IOException("Too many change-order entries");
        Set<String> orderIds=new HashSet<>(),lineIds=new HashSet<>();
        for(int i=1;i<orders.size();i++) {
            List<String> order=orders.get(i);
            if(!order.get(0).matches("CO-[a-f0-9]{32}")||
                !orderIds.add(order.get(0))||order.get(1).isEmpty()||
                !Arrays.asList("Proposed","Acknowledged",
                    "Invoiced").contains(order.get(2)))
                throw new IOException("Invalid change order in backup");
        }
        for(int i=1;i<lines.size();i++){
            List<String> line=lines.get(i);
            if(!line.get(0).matches("COL-[a-f0-9]{32}")||
                !lineIds.add(line.get(0))||!orderIds.contains(line.get(1))||
                line.get(2).trim().isEmpty())
                throw new IOException("Invalid change-order line in backup");
            try{ChangeOrderProof.total(java.util.Collections.singletonList(line));}
            catch(IllegalArgumentException e){
                throw new IOException("Invalid change-order amount in backup",e);
            }
        }
        for(int i=1;i<orders.size();i++){
            List<String> order=orders.get(i);
            String id=order.get(0);
            List<List<String>> subset=new ArrayList<>();
            for(int k=1;k<lines.size();k++)if(id.equals(lines.get(k).get(1)))
                subset.add(lines.get(k));
            if("Proposed".equals(order.get(2))) {
                if(!order.get(4).isEmpty()||!order.get(5).isEmpty()||
                    !order.get(6).isEmpty()||!order.get(7).isEmpty())
                    throw new IOException("Unsigned change order has signoff metadata");
                continue;
            }
            if(subset.isEmpty()||order.get(4).isEmpty()||order.get(5).isEmpty())
                throw new IOException("Acknowledged change order has no evidence");
            File sig=new File(root,folder+"/change_order_signatures/"+id+".png");
            if(!sig.isFile()||Files.isSymbolicLink(sig.toPath())||
                sig.length()<100||sig.length()>256*1024)
                throw new IOException("Change-order signature missing or oversized");
            byte[] png=Files.readAllBytes(sig.toPath());
            byte[] magic={(byte)137,80,78,71,13,10,26,10};
            for(int k=0;k<magic.length;k++)if(png[k]!=magic[k])
                throw new IOException("Invalid change-order PNG");
            if(!ChangeOrderProof.sha256(png).equals(order.get(6))||
                !ChangeOrderProof.contentHash(jobId,id,order.get(1),order.get(4),
                    order.get(5),order.get(6),subset).equals(order.get(7)))
                throw new IOException("Change-order integrity check failed");
            List<List<String>> billed=rows(root,folder+"/job_items.csv",ITEM);
            for(List<String> signedLine:subset){
                String expectedDescription=signedLine.get(2)+" [CO:"+signedLine.get(0)+"]";
                int found=0;
                for(int n=1;n<billed.size();n++){
                    List<String> posted=billed.get(n);
                    if(posted.get(1).endsWith("[CO:"+signedLine.get(0)+"]")){
                        found++;
                        try{
                            if(!posted.get(1).equals(expectedDescription)||
                                new BigDecimal(posted.get(2)).compareTo(
                                    new BigDecimal(signedLine.get(3)))!=0||
                                new BigDecimal(posted.get(3)).compareTo(
                                    new BigDecimal(signedLine.get(4)))!=0||
                                new BigDecimal(posted.get(4)).compareTo(
                                    new BigDecimal(signedLine.get(5)))!=0)
                                throw new IOException("Billed change-order line differs from approval");
                        }catch(NumberFormatException e){
                            throw new IOException("Invalid billed change-order amount",e);
                        }
                    }
                }
                if(found>1 || ("Invoiced".equals(order.get(2))&&found!=1))
                    throw new IOException("Duplicate or missing billed change-order line");
            }
        }
    }

    /** Validate IDs, foreign keys, canonical billing rows and required files. */
    public static void validate(File root) throws IOException {
        if (!root.isDirectory() || Files.isSymbolicLink(root.toPath()))
            throw new IOException("Workspace root is missing or unsafe");
        List<List<String>> clients = rows(root, "master_data/customers.csv", CUSTOMER);
        List<List<String>> jobs = rows(root, "master_data/jobs.csv", JOB);
        rows(root, "master_data/catalog.csv", CATALOG);
        rows(root, "master_data/expenses.csv", EXPENSE);
        // Portable setup preferences are optional for legacy workspaces.
        // Reject malformed or edited switches before activating a ZIP restore.
        File businessSetup=new File(root,"templates/business_setup.csv");
        if(businessSetup.isFile()){
            if(businessSetup.length()>4096)throw new IOException("Business setup too large");
            byte[] setupBytes=Files.readAllBytes(businessSetup.toPath());
            String setupText;
            try{
                setupText=StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(java.nio.ByteBuffer.wrap(setupBytes)).toString();
            }catch(java.nio.charset.CharacterCodingException error){
                throw new IOException("Setup data must be valid UTF-8",error);
            }
            BusinessSetupProfile.fromCsv(setupText);
        }
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
        if(new File(root,"master_data/calendar_links.csv").isFile()){
            List<List<String>> links=rows(root,"master_data/calendar_links.csv",
                new String[]{"JobID","CalendarID","EventID"});
            Set<String> linkKeys=new HashSet<>();
            for(int i=1;i<links.size();i++){
                List<String> values=links.get(i);
                if(!values.get(0).matches("JOB-[a-f0-9]{32}")||
                    !values.get(1).matches("[0-9]{1,18}")||
                    !values.get(2).matches("[0-9]{1,18}")||
                    !linkKeys.add(values.get(0)+"|"+values.get(1)))
                    throw new IOException("Invalid calendar link record");
            }
        }
        if(new File(root,"master_data/pricebook.csv").isFile()){
            List<List<String>> book=rows(root,"master_data/pricebook.csv",PRICEBOOK);
            Set<String> ids=new HashSet<>();
            for(int i=1;i<book.size();i++){
                List<String> r=book.get(i);
                if(!r.get(0).matches("CAT-[a-f0-9]{32}")||!ids.add(r.get(0)))
                    throw new IOException("Invalid pricebook item ID");
                try {
                    BigDecimal cost=new BigDecimal(r.get(4));
                    BigDecimal markup=new BigDecimal(r.get(5));
                    if(cost.signum()<0||cost.scale()>2||markup.compareTo(
                        new BigDecimal("-100"))<0||markup.compareTo(
                        new BigDecimal("1000"))>0)
                        throw new IOException("Invalid base price/markup");
                }catch(NumberFormatException e){throw new IOException("Invalid pricing number",e);}
            }
        }
        if(new File(root,"master_data/contacts.csv").isFile()){
            List<List<String>> contacts=rows(root,"master_data/contacts.csv",CONTACTS);
            Set<String> keys=new HashSet<>();
            for(int i=1;i<contacts.size();i++){
                List<String> item=contacts.get(i);
                if(!item.get(0).matches("CONT-[a-f0-9]{32}")||
                    !keys.add(item.get(0))||item.get(1).trim().isEmpty()||
                    item.get(1).length()>180||
                    (!item.get(5).isEmpty()&&!folders.containsKey(item.get(5))))
                    throw new IOException("Invalid contact directory entry");
            }
        }
        if(new File(root,"templates/job_fields.csv").isFile()){
            List<List<String>> templates=rows(root,"templates/job_fields.csv",JOB_MASTER);
            verifyFlexibleFields(templates,false);
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
            String photoIndex=jobFolder+"/photo_order.csv";
            if(new File(root,photoIndex).isFile()){
                List<List<String>> ordered=rows(root,photoIndex,PHOTO_ORDER);
                Set<String> seenPhotos=new HashSet<>();
                if(ordered.size()>2001)throw new IOException("Too many indexed photos");
                for(int n=1;n<ordered.size();n++){
                    List<String> row=ordered.get(n);
                    String photo=row.get(0);
                    if(!PhotoOrdering.valid(photo)||!seenPhotos.add(photo)||
                        !row.get(1).equals(Integer.toString(n-1))||
                        !new File(root,jobFolder+"/photos/"+photo).isFile())
                        throw new IOException("Corrupt photo order index");
                }
            }
            String custom=jobFolder+"/custom_fields.csv";
            if(new File(root,custom).isFile()){
                List<List<String>> jobFields=rows(root,custom,JOB_FIELD);
                verifyFlexibleFields(jobFields,true);
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
                    }catch(java.time.format.DateTimeParseException|NumberFormatException parseError){
                        throw new IOException("Invalid time record",parseError);
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
            String milestonesPath=jobFolder+"/job_milestones.csv";
            if(new File(root,milestonesPath).isFile()){
                List<List<String>> milestones=rows(root,milestonesPath,MILESTONE);
                Set<String> ids=new HashSet<>();
                for(int k=1;k<milestones.size();k++){
                    List<String> m=milestones.get(k);
                    if(!m.get(0).matches("MILE-[a-f0-9]{32}")||!ids.add(m.get(0))||
                        !(m.get(2).equals("true")||m.get(2).equals("false")))
                        throw new IOException("Invalid milestone");
                    if(!m.get(3).isEmpty()){
                        try{java.time.Instant.parse(m.get(3));}
                        catch(java.time.format.DateTimeParseException e){
                            throw new IOException("Invalid milestone timestamp",e);}
                    }
                }
            }
            String pickupPath=jobFolder+"/pickup_reminder.csv";
            if(new File(root,pickupPath).isFile()){
                List<List<String>> reminders=rows(root,pickupPath,PICKUP);
                if(reminders.size()!=2)throw new IOException("Invalid pickup reminder count");
                List<String> v=reminders.get(1);
                try{
                    java.time.Instant.parse(v.get(0));
                    java.time.Instant.parse(v.get(1));
                }catch(java.time.format.DateTimeParseException e){
                    throw new IOException("Invalid pickup timestamp",e);
                }
                if(!v.get(2).equals("Scheduled"))
                    throw new IOException("Invalid pickup reminder status");
            }
            String logisticsPath=jobFolder+"/job_logistics.csv";
            if(new File(root,logisticsPath).isFile()){
                List<List<String>> rows=rows(root,logisticsPath,LOGISTICS);
                if(rows.size()>2)throw new IOException("Repeated job logistics record");
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
            validateChangeOrders(root,jobFolder,id);
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
        File scheduleFile=new File(root,"master_data/service_intervals.csv");
        if(scheduleFile.isFile()){
            List<List<String>> schedules=rows(root,"master_data/service_intervals.csv",
                SERVICE_INTERVALS);
            if(schedules.size()>2001)throw new IOException("Too many service intervals");
            Map<String,String> customerOfJob=new HashMap<>();
            for(int i=1;i<jobs.size();i++)
                customerOfJob.put(jobs.get(i).get(0),jobs.get(i).get(1));
            Set<String> scheduleIds=new HashSet<>();
            for(int i=1;i<schedules.size();i++){
                List<String> rule=schedules.get(i);
                if(!rule.get(0).matches("SERVICE-[a-f0-9]{32}") ||
                    !scheduleIds.add(rule.get(0))||
                    !rule.get(1).equals(customerOfJob.get(rule.get(2)))||
                    rule.get(3).trim().isEmpty()||rule.get(3).length()>180||
                    rule.get(4).length()>180||
                    !Arrays.asList("true","false").contains(rule.get(11)))
                    throw new IOException("Invalid or orphaned recurring service schedule");
                try{
                    int months=Integer.parseInt(rule.get(6));
                    if(months<0||months>120)throw new IllegalArgumentException();
                    int miles=Integer.parseInt(rule.get(8));
                    if(miles<0||miles>1000000)throw new IllegalArgumentException();
                    if(!rule.get(7).isEmpty()){
                        long reading=Long.parseLong(rule.get(7));
                        if(reading<0||reading>9999999)throw new IllegalArgumentException();
                    }
                    String dueDate=ServiceIntervals.dueDate(rule.get(5),months);
                    String dueMiles=ServiceIntervals.dueMileage(rule.get(7),rule.get(8));
                    if(months==0&&miles==0||!rule.get(9).equals(dueDate)||
                        !rule.get(10).equals(dueMiles))
                        throw new IOException("Recurring schedule due values were altered");
                }catch(IllegalArgumentException error){
                    throw new IOException("Invalid service months/mileage in backup",error);
                }
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
