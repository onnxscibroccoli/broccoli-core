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
        System.out.println("BackupArchiveSmoke: PASS (validation, traversal, rollback, crash)");
    }
}
