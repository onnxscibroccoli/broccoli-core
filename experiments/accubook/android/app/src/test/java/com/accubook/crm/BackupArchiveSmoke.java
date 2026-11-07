package com.accubook.crm;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Dependency-free JVM regression tests for restore safety and CSV relationships. */
public final class BackupArchiveSmoke {
    private BackupArchiveSmoke() {}
    private static final String[] CUSTOMER = {"CustomerID","CompanyName","ContactName",
        "Phone","Email","BillingStreet","BillingCity","BillingState","BillingZip","FolderPath"};
    private static final String[] JOB = {"JobID","CustomerID","JobTitle","JobStreet",
        "JobCity","JobState","JobZip","Status","ScheduledDate","TotalAmount"};
    private static final String[] ITEM = {"ItemID","Description","Quantity","UnitRate","LineTotal"};
    private static final String[] CATALOG = {"ItemID","Category","ItemName","DefaultUnit","DefaultRate"};
    private static final String[] EXPENSE = {"ExpenseID","Date","Category","Description","Amount"};

    private static List<String> row(String... fields) {
        return new ArrayList<>(Arrays.asList(fields));
    }
    private static void table(File base, String relative, String[] header,
                              List<String>... values) throws IOException {
        File path = new File(base, relative);
        Files.createDirectories(path.getParentFile().toPath());
        List<List<String>> rows = new ArrayList<>();
        rows.add(row(header));
        rows.addAll(Arrays.asList(values));
        Files.writeString(path.toPath(), CsvCodec.write(rows), StandardCharsets.UTF_8);
    }
    private static void workspace(File root, boolean full) throws IOException {
        String cid = "CUST-" + "a".repeat(32);
        String jid = "JOB-" + "b".repeat(32);
        String directory = "customers/" + cid + "_Example";
        if (full) {
            table(root, "master_data/customers.csv", CUSTOMER,
                row(cid,"Example","","555-0111","example@example.com","1 Main St",
                    "Boston","MA","02108",directory));
            table(root, "master_data/jobs.csv", JOB,
                row(jid,cid,"Gutter","","Boston","MA","02108","Scheduled",
                    "2026-11-07","20.00"));
            String jdir = directory + "/jobs/" + jid + "_Gutter";
            table(root, jdir + "/job_items.csv", ITEM,
                row("CUSTOM-1", "Labor","2","10.00","20.00"));
            table(root, jdir + "/material_requests.csv",
                new String[]{"RequestID","Description","Quantity","Unit","Status"},
                row("REQ-" + "d".repeat(32),"Shingle bundles","3","bundle","Requested"));
            Files.writeString(new File(root, jdir + "/field_notes.md").toPath(),
                "Gate: ask owner before entering", StandardCharsets.UTF_8);
            File photo = new File(root, jdir + "/photos/PHOTO-" + "c".repeat(32) + ".jpg");
            Files.createDirectories(photo.getParentFile().toPath());
            Files.write(photo.toPath(), new byte[]{(byte)255,(byte)216,(byte)255,0,1,2});
            table(root,jdir+"/photo_order.csv",
                new String[]{"PhotoFile","Position"},
                row("PHOTO-"+"c".repeat(32)+".jpg","0"));
            table(root,directory+"/contact_preferences.csv",
                new String[]{"Call","SMS","Email","Color"},
                row("true","false","true","#165DAB"));
            table(root,jdir+"/appointment.csv",
                new String[]{"StartTime","EndTime","Color","DaybookNote"},
                row("09:00","10:30","#137C66","Roof visit"));
            table(root,jdir+"/quote.csv",
                new String[]{"QuoteSent","DateSent","QuoteNote"},
                row("true","2026-11-07","Sent via email"));
            table(root,jdir+"/payments.csv",
                new String[]{"PaymentID","Date","Method","Amount","Reference","Notes"},
                row("PAY-"+"e".repeat(32),"2026-11-07","Cash","10.00","R1","Deposit"));
            table(root,jdir+"/invoice_memo.csv",new String[]{"Greeting","Closing"},
                row("Welcome","Thank you"));
            table(root,jdir+"/attachments.csv",
                new String[]{"AttachmentID","DisplayName","MimeType","SizeBytes","StoredName"},
                row("ATT-"+"f".repeat(32),"spec.pdf","application/pdf","5",
                    "ATT-"+"f".repeat(32)+".bin"));
            File attachment=new File(root,jdir+"/attachments/ATT-"+"f".repeat(32)+".bin");
            Files.createDirectories(attachment.getParentFile().toPath());
            Files.write(attachment.toPath(),new byte[]{1,2,3,4,5});
            table(root,"templates/branding.csv",
                new String[]{"BusinessName","Address","Phone","Email","AccentColor","Terms","Footer","LogoMimeType"},
                row("Demo LLC","Boston, MA","555-0100","demo@example.invalid",
                    "#165DAB","Pay on delivery","Thank you",""));
            Files.writeString(new File(root,"templates/business_setup.csv").toPath(),
                new BusinessSetupProfile("COMPLETE","SOLO","Gutters","ABC Supply",
                    true,true,false,true,false,false,false,true).toCsv(),
                StandardCharsets.UTF_8);
            String inventoryId="INV-"+"1".repeat(32);
            table(root,"master_data/inventory_items.csv",StockLedger.ITEMS,
                row(inventoryId,"Shingle bundles","MATERIAL","bundle","true"));
            table(root,"master_data/inventory_movements.csv",StockLedger.MOVES,
                row("MOVE-"+"1".repeat(32),inventoryId,"2026-11-07T11:00:00Z",
                    "RECEIVE","EXTERNAL","COMPANY","6","Delivery"),
                row("MOVE-"+"2".repeat(32),inventoryId,"2026-11-07T11:30:00Z",
                    "TRANSFER","COMPANY",jid,"2","Site delivery"));
            table(root,"master_data/pricebook.csv",
                new String[]{"CatalogID","Category","Name","Unit","BaseCost",
                    "MarkupPercent","Supplier","UpdatedUTC"},
                row("CAT-"+"a".repeat(32),"Gutter Cleaning","Standard gutter cleaning",
                    "service","250.00","0","Manual","2026-11-07T00:00:00Z"));
            table(root,"master_data/service_intervals.csv",
                new String[]{"ScheduleID","CustomerID","SourceJobID","ServiceLabel","SiteName",
                    "LastServiceDate","IntervalMonths","LastMileage","IntervalMiles",
                    "DueDate","DueMileage","Active"},
                row("SERVICE-"+"5".repeat(32),cid,jid,
                    "Oil service","Truck 1","2026-05-07","6","55812","3000",
                    "2026-11-07","58812","true"));
            table(root,"master_data/calendar_links.csv",
                new String[]{"JobID","CalendarID","EventID"},
                row(jid,"123","456"));
            table(root,jdir+"/time_entries.csv",
                new String[]{"EntryID","Worker","StartedAt","EndedAt","Hours","Notes"},
                row("TIME-"+"1".repeat(32),"Crew A","2026-11-07T12:00:00Z",
                    "2026-11-07T13:30:00Z","1.5000","Test"));
            table(root,jdir+"/route_points.csv",
                new String[]{"RecordedAt","Latitude","Longitude","AccuracyMeters"},
                row("2026-11-07T12:30:00Z","42.24","-70.88","15.0"));
            table(root,jdir+"/job_milestones.csv",
                new String[]{"Key","Name","Complete","CompletedUTC","Notes"},
                row("MILE-"+"2".repeat(32),"Dumpster delivered","true",
                    "2026-11-07T11:00:00Z","Delivered"));
            table(root,jdir+"/job_logistics.csv",
                new String[]{"Vendor","MaterialDeliveryContact","AssignedCrew","OperationsNotes"},
                row("Sample Dumpster","Material Driver","Crew A","Demo"));
            table(root,jdir+"/pickup_reminder.csv",
                new String[]{"DueAtUTC","ConfiguredAtUTC","State"},
                row("2026-11-08T12:00:00Z","2026-11-07T12:00:00Z","Scheduled"));
            table(root,"master_data/contacts.csv",
                new String[]{"ContactID","Name","Phone","Email","SourceID","CustomerID"},
                row("CONT-"+"1".repeat(32),"Example Contact","555-0188",
                    "contact@example.invalid","android:23",""));
            table(root,"templates/job_fields.csv",
                new String[]{"FieldID","Label","Kind","Required","DefaultValue","Active"},
                row("FIELD-"+"2".repeat(32),"On-site estimate visit",
                    "Checkbox","true","false","true"),
                row("FIELD-"+"3".repeat(32),"Equipment delivered",
                    "Checkbox","false","false","true"));
            table(root,jdir+"/custom_fields.csv",
                new String[]{"FieldID","Label","Kind","Required","Value","Active","Origin"},
                row("FIELD-"+"2".repeat(32),"Site inspection completed",
                    "Checkbox","true","true","true","Master"),
                row("FIELD-"+"4".repeat(32),"Special access instructions",
                    "Text","false","Use rear gate","true","Job"));
            File profile = new File(root, directory + "/profile.md");
            Files.createDirectories(profile.getParentFile().toPath());
            Files.writeString(profile.toPath(), "# notes\n", StandardCharsets.UTF_8);
        } else {
            table(root, "master_data/customers.csv", CUSTOMER);
            table(root, "master_data/jobs.csv", JOB);
        }
        table(root, "master_data/catalog.csv", CATALOG);
        table(root, "master_data/expenses.csv", EXPENSE);
    }
    private static void zipTree(File root, File folder, ZipOutputStream zip) throws IOException {
        File[] children = folder.listFiles();
        if (children == null) throw new IOException("Missing directory");
        for (File child : children) {
            if (child.isDirectory()) { zipTree(root, child, zip); continue; }
            String name = root.toPath().relativize(child.toPath()).toString().replace('\\','/');
            zip.putNextEntry(new ZipEntry(name));
            try (FileInputStream input = new FileInputStream(child)) {
                input.transferTo(zip);
            }
            zip.closeEntry();
        }
    }
    private static byte[] zip(File root) throws IOException {
        ByteArrayOutputStream destination = new ByteArrayOutputStream();
        try (ZipOutputStream output = new ZipOutputStream(destination, StandardCharsets.UTF_8)) {
            zipTree(root, root, output);
        }
        return destination.toByteArray();
    }
    private static byte[] malicious(String entry) throws IOException {
        ByteArrayOutputStream destination = new ByteArrayOutputStream();
        try (ZipOutputStream output = new ZipOutputStream(destination, StandardCharsets.UTF_8)) {
            output.putNextEntry(new ZipEntry(entry));
            output.write("unsafe".getBytes(StandardCharsets.UTF_8));
            output.closeEntry();
        }
        return destination.toByteArray();
    }
    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        File tmp = Files.createTempDirectory("accubook-archive-smoke-").toFile();
        File live = new File(tmp, "Accubook Workspace");
        File source = new File(tmp, "source");
        workspace(live, false);
        workspace(source, true);
        BackupArchive.validate(live);
        BackupArchive.validate(source);
        byte[] good = zip(source);
        byte[] original = Files.readAllBytes(
            new File(live, "master_data/customers.csv").toPath());

        for (String bad : new String[]{"../pwn.txt", "/etc/passwd",
            "customers/CUST-" + "a".repeat(32) + "_Example/secret.sh"}) {
            boolean rejected = false;
            try { BackupArchive.restore(live, new ByteArrayInputStream(malicious(bad))); }
            catch (IOException expected) { rejected = true; }
            check(rejected, "Unsafe ZIP accepted: " + bad);
            check(!new File(tmp, "pwn.txt").exists(), "Traversal escaped workspace");
            check(Arrays.equals(original,
                Files.readAllBytes(new File(live, "master_data/customers.csv").toPath())),
                "A rejected backup modified current records");
        }

        BackupArchive.restore(live, new ByteArrayInputStream(good));
        BackupArchive.validate(live);
        check(BackupArchive.rollback(live).isDirectory(), "Previous snapshot missing");
        check(Files.readString(new File(live,"master_data/customers.csv").toPath())
            .contains("Example"), "Imported customer absent");
        String jdir = "customers/CUST-" + "a".repeat(32) + "_Example/jobs/JOB-"
            + "b".repeat(32) + "_Gutter";
        check(Files.readString(new File(live, jdir + "/material_requests.csv").toPath())
            .contains("Shingle bundles"), "Materials not restored");
        check(Files.readString(new File(live, jdir + "/field_notes.md").toPath())
            .contains("Gate:"), "Field notes not restored");
        check(Files.readString(new File(live,jdir+"/appointment.csv").toPath())
            .contains("09:00"),"Appointment time missing");
        check(Files.readString(new File(live,jdir+"/quote.csv").toPath())
            .contains("true"),"Quote status missing");
        check(Files.readString(new File(live,jdir+"/payments.csv").toPath())
            .contains("Cash"),"Payment ledger missing");
        check(Files.readString(new File(live,jdir+"/time_entries.csv").toPath())
            .contains("1.5000"),"Work time not restored");
        check(Files.readString(new File(live,jdir+"/job_milestones.csv").toPath())
            .contains("Dumpster delivered"),"Milestones not restored");
        check(Files.readString(new File(live,"master_data/contacts.csv").toPath())
            .contains("Example Contact"),"Imported contact directory not preserved");
        check(Files.readString(new File(live,"templates/job_fields.csv").toPath())
            .contains("On-site estimate visit"),"Master job template not restored");
        check(Files.readString(new File(live,jdir+"/custom_fields.csv").toPath())
            .contains("Use rear gate"),"Per-job custom field not restored");
        check(Files.readString(new File(live,jdir+"/photo_order.csv").toPath())
            .contains("PHOTO-"),"Photo display order not restored");
        check(Files.readString(new File(live,jdir+"/job_logistics.csv").toPath())
            .contains("Sample Dumpster"),"Vendor logistics not restored");
        check(Files.readString(new File(live,jdir+"/pickup_reminder.csv").toPath())
            .contains("Scheduled"),"Pickup alarm metadata not restored");
        check(Files.readString(new File(live,"master_data/pricebook.csv").toPath())
            .contains("250.00"),"Catalog pricing not restored");
        check(Files.readString(new File(live,"master_data/calendar_links.csv").toPath())
            .contains("456"),"Calendar mapping not restored");
        BusinessSetupProfile recovered=BusinessSetupProfile.fromCsv(
            Files.readString(new File(live,"templates/business_setup.csv").toPath()));
        check(recovered.status.equals("COMPLETE")&&recovered.recurring
            &&recovered.vendors.equals("ABC Supply"),
            "Portable business setup lost in restore");
        check(Files.readString(new File(live,"master_data/inventory_items.csv").toPath())
            .contains("Shingle bundles"),"Inventory item catalog not restored");
        List<List<String>> stock=CsvCodec.read(
            Files.readString(new File(live,"master_data/inventory_items.csv").toPath()));
        List<List<String>> moves=CsvCodec.read(
            Files.readString(new File(live,"master_data/inventory_movements.csv").toPath()));
        StockLedger.State counts=StockLedger.validate(stock,moves,
            new java.util.HashSet<>(java.util.Arrays.asList("JOB-"+"b".repeat(32))));
        check(counts.balance("INV-"+"1".repeat(32),"COMPANY").intValueExact()==4,
            "Company stock lost during backup restore");
        check(counts.balance("INV-"+"1".repeat(32),"JOB-"+"b".repeat(32))
            .intValueExact()==2,"Job-site stock lost during backup restore");
        check(Files.readString(new File(live,"master_data/service_intervals.csv").toPath())
            .contains("58812"),"Service mileage interval lost in backup");

        check(Files.readAllBytes(new File(live,jdir+"/attachments/ATT-"+
            "f".repeat(32)+".bin").toPath()).length==5,"Attachment missing");
        File invalid=new File(tmp,"corrupt");
        workspace(invalid,true);
        table(invalid,jdir+"/payments.csv",
            new String[]{"PaymentID","Date","Method","Amount","Reference","Notes"},
            row("PAY-"+"e".repeat(32),"2026-11-07","Cash","-100.00","",""));
        boolean rejectedLedger=false;
        try{BackupArchive.validate(invalid);}
        catch(IOException expected){rejectedLedger=true;}
        check(rejectedLedger,"Corrupt payment ledger was accepted");
        table(invalid,jdir+"/custom_fields.csv",
            new String[]{"FieldID","Label","Kind","Required","Value","Active","Origin"},
            row("FIELD-"+"2".repeat(32),"Broken required flag","Checkbox",
                "maybe","true","true","Master"));
        boolean rejectedFields=false;
        try{BackupArchive.validate(invalid);}
        catch(IOException expected){rejectedFields=true;}
        check(rejectedFields,"Malformed required job field was accepted");
        File wrongDue=new File(tmp,"invalid-service-due");
        workspace(wrongDue,true);
        table(wrongDue,"master_data/service_intervals.csv",
            new String[]{"ScheduleID","CustomerID","SourceJobID","ServiceLabel","SiteName",
                "LastServiceDate","IntervalMonths","LastMileage","IntervalMiles",
                "DueDate","DueMileage","Active"},
            row("SERVICE-"+"5".repeat(32),"CUST-"+"a".repeat(32),
                "JOB-"+"b".repeat(32),"Oil service","Truck 1","2026-05-07",
                "6","55812","3000","2026-12-07","58812","true"));
        boolean refusedDue=false;
        try{BackupArchive.validate(wrongDue);}
        catch(IOException expected){refusedDue=true;}
        check(refusedDue,"Altered due date accepted in backup");

        File badSetup=new File(tmp,"tampered-business-setup");
        workspace(badSetup,true);
        File setupCsv=new File(badSetup,"templates/business_setup.csv");
        Files.writeString(setupCsv.toPath(),
            Files.readString(setupCsv.toPath()).replace("COMPLETE","INVALID"),
            StandardCharsets.UTF_8);
        boolean rejectedSetup=false;
        try{BackupArchive.validate(badSetup);}
        catch(IOException expected){rejectedSetup=true;}
        check(rejectedSetup,"Malformed restored business setup was accepted");
        File badStock=new File(tmp,"tampered-inventory");
        workspace(badStock,true);
        table(badStock,"master_data/inventory_movements.csv",StockLedger.MOVES,
            row("MOVE-"+"1".repeat(32),"INV-"+"1".repeat(32),
                "2026-11-07T11:00:00Z","RECEIVE","EXTERNAL","COMPANY","1","received"),
            row("MOVE-"+"2".repeat(32),"INV-"+"1".repeat(32),
                "2026-11-07T11:30:00Z","TRANSFER","COMPANY",
                "JOB-"+"b".repeat(32),"99","invalid transfer"));
        boolean rejectedInventory=false;
        try{BackupArchive.validate(badStock);}
        catch(IOException expected){rejectedInventory=true;}
        check(rejectedInventory,"Tampered inventory stock accepted in backup");
        File badPhotos=new File(tmp,"bad-photo-order");
        workspace(badPhotos,true);
        table(badPhotos,jdir+"/photo_order.csv",
            new String[]{"PhotoFile","Position"},
            row("PHOTO-"+"c".repeat(32)+".jpg","4"));
        boolean rejectedPhotoIndex=false;
        try{BackupArchive.validate(badPhotos);}
        catch(IOException expected){rejectedPhotoIndex=true;}
        check(rejectedPhotoIndex,"Malformed photo sort index accepted");
        boolean refused = false;
        try { BackupArchive.restore(live, new ByteArrayInputStream(good)); }
        catch (IOException expected) { refused = true; }
        check(refused, "Restore overwrote retained rollback");
        BackupArchive.clearPreviousSnapshot(live);
        check(!BackupArchive.rollback(live).exists(), "Explicit discard did not complete");
        BackupArchive.restore(live, new ByteArrayInputStream(good));

        // Crash after live -> previous, before staged -> live.
        File previous = BackupArchive.rollback(live);
        check(previous.isDirectory(), "Second restore did not retain snapshot");
        BackupArchive.revertPreviousSnapshot(live);
        check(live.isDirectory(), "Revert did not reopen valid workspace");
        check(!previous.exists(), "Previous snapshot not consumed by revert");
        check(new File(tmp, "Accubook Workspace.failed-live").isDirectory(),
            "Revert destroyed the newer workspace");
        BackupArchive.validate(live);

        // Interruption recovery without any silent data initialization.
        check(live.renameTo(previous), "Cannot simulate rename interruption");
        BackupArchive.recover(live);
        check(live.isDirectory(), "Crash recovery failed to reopen previous");
        BackupArchive.validate(live);

        // Signed change orders must survive ZIP export and reject altered evidence.
        File signed=new File(tmp,"signed-workspace");
        workspace(signed,true);
        String coId="CO-"+"6".repeat(32),coLineId="COL-"+"7".repeat(32);
        byte[] png=new byte[128];
        byte[] magic={(byte)137,80,78,71,13,10,26,10};
        System.arraycopy(magic,0,png,0,magic.length);
        String signedName=jdir+"/change_order_signatures/"+coId+".png";
        File signature=new File(signed,signedName);
        Files.createDirectories(signature.getParentFile().toPath());
        Files.write(signature.toPath(),png);
        List<List<String>> signedLines=new ArrayList<>();
        signedLines.add(row(coLineId,coId,"Extra downspout","2","25.00","50.00"));
        table(signed,jdir+"/change_order_lines.csv",
            new String[]{"LineID","ChangeOrderID","Description","Quantity","UnitRate","Amount"},
            signedLines.get(0));
        String at="2026-11-07T19:20:00Z",sigHash=ChangeOrderProof.sha256(png);
        String contentHash=ChangeOrderProof.contentHash("JOB-"+"b".repeat(32),coId,
            "Customer-approved work",at,"Sample Signer",sigHash,signedLines);
        table(signed,jdir+"/change_orders.csv",
            new String[]{"ChangeOrderID","Title","Status","CreatedUTC","AcknowledgedUTC",
                "SignedBy","SignatureSHA256","ContentSHA256"},
            row(coId,"Customer-approved work","Acknowledged",
                "2026-11-07T19:00:00Z",at,"Sample Signer",sigHash,contentHash));
        BackupArchive.validate(signed);
        File restoredSigned=new File(tmp,"restored-signed-workspace");
        BackupArchive.restore(restoredSigned,new ByteArrayInputStream(zip(signed)));
        BackupArchive.validate(restoredSigned);
        check(Files.isRegularFile(new File(restoredSigned,signedName).toPath()),
            "Acknowledgement PNG lost in restore");
        table(signed,jdir+"/change_order_lines.csv",
            new String[]{"LineID","ChangeOrderID","Description","Quantity","UnitRate","Amount"},
            row(coLineId,coId,"Different unauthorized work","2","25.00","50.00"));
        boolean rejectedSigned=false;
        try{BackupArchive.validate(signed);}catch(IOException expected){rejectedSigned=true;}
        check(rejectedSigned,"Tampered signed change order was accepted");
        // An invoiced order must preserve each signed line and the cached total.
        table(signed,jdir+"/change_order_lines.csv",
            new String[]{"LineID","ChangeOrderID","Description","Quantity","UnitRate","Amount"},
            row(coLineId,coId,"Extra downspout","2","25.00","50.00"));
        table(signed,jdir+"/change_orders.csv",
            new String[]{"ChangeOrderID","Title","Status","CreatedUTC","AcknowledgedUTC",
                "SignedBy","SignatureSHA256","ContentSHA256"},
            row(coId,"Customer-approved work","Invoiced",
                "2026-11-07T19:00:00Z",at,"Sample Signer",sigHash,contentHash));
        table(signed,jdir+"/job_items.csv",ITEM,
            row("CUSTOM-1","Labor","2","10.00","20.00"),
            row("CUSTOM-2","Extra downspout [CO:"+coLineId+"]","2","25.00","50.00"));
        table(signed,"master_data/jobs.csv",JOB,
            row("JOB-"+"b".repeat(32),"CUST-"+"a".repeat(32),
                "Gutter","","Boston","MA","02108","Scheduled","2026-11-07","70.00"));
        BackupArchive.validate(signed);
        table(signed,jdir+"/job_items.csv",ITEM,
            row("CUSTOM-1","Labor","2","10.00","20.00"),
            row("CUSTOM-2","Unauthorized description [CO:"+coLineId+"]",
                "2","25.00","50.00"));
        boolean refusedChangedInvoice=false;
        try{BackupArchive.validate(signed);}
        catch(IOException expected){refusedChangedInvoice=true;}
        check(refusedChangedInvoice,"Altered billed description was accepted");
        table(signed,jdir+"/job_items.csv",ITEM,
            row("CUSTOM-1","Labor","2","10.00","20.00"));
        boolean refusedMissingInvoice=false;
        try{BackupArchive.validate(signed);}
        catch(IOException expected){refusedMissingInvoice=true;}
        check(refusedMissingInvoice,"Missing invoiced change-order line was accepted");


        System.out.println("BackupArchiveSmoke: PASS (validation, traversal, rollback, crash)");
    }
}
