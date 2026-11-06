package com.accubook.crm;

import android.content.Context;
import android.util.AtomicFile;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * Isolated, non-root, offline storage domain for Accubook.
 *
 * App-private directory. Mutations are serialized within this app instance.
 * AtomicFile protects individual files, not cross-file transaction sets.
 */
public final class WorkspaceStore {
    private static final String[] CUSTOMER_HEADER = {
        "CustomerID", "CompanyName", "ContactName", "Phone", "Email",
        "BillingStreet", "BillingCity", "BillingState", "BillingZip", "FolderPath"
    };
    private static final String[] JOB_HEADER = {
        "JobID", "CustomerID", "JobTitle", "JobStreet", "JobCity", "JobState",
        "JobZip", "Status", "ScheduledDate", "TotalAmount"
    };
    private static final String[] ITEM_HEADER = {
        "ItemID", "Description", "Quantity", "UnitRate", "LineTotal"
    };
    private static final String[] CATALOG_HEADER = {
        "ItemID", "Category", "ItemName", "DefaultUnit", "DefaultRate"
    };
    private static final String[] EXPENSE_HEADER = {
        "ExpenseID", "Date", "Category", "Description", "Amount"
    };

    public static final class Customer {
        public final String id, company, contact, phone, email, street, city, state, zip, folder;
        Customer(List<String> r) {
            id=r.get(0); company=r.get(1); contact=r.get(2); phone=r.get(3);
            email=r.get(4); street=r.get(5); city=r.get(6); state=r.get(7);
            zip=r.get(8); folder=r.get(9);
        }
        public String displayName() {
            return company.isEmpty() ? contact : company + " — " + contact;
        }
    }

    public static final class Job {
        public final String id, customerId, title, street, city, state, zip, status, date, total;
        Job(List<String> r) {
            id=r.get(0); customerId=r.get(1); title=r.get(2); street=r.get(3);
            city=r.get(4); state=r.get(5); zip=r.get(6); status=r.get(7);
            date=r.get(8); total=r.get(9);
        }
    }

    public static final class LineItem {
        public final String id, description, quantity, unitRate, amount;
        LineItem(List<String> r) {
            id=r.get(0); description=r.get(1); quantity=r.get(2);
            unitRate=r.get(3); amount=r.get(4);
        }
    }

    private final File root;
    private final File master;
    private final File customersFile;
    private final File jobsFile;
    private final File catalogFile;
    private final File expensesFile;

    public WorkspaceStore(Context context) throws IOException {
        root = new File(context.getFilesDir(), "Accubook Workspace");
        BackupArchive.recover(root);
        master = new File(root, "master_data");
        customersFile = new File(master, "customers.csv");
        jobsFile = new File(master, "jobs.csv");
        catalogFile = new File(master, "catalog.csv");
        expensesFile = new File(master, "expenses.csv");
        directory(master);
        directory(new File(root, "customers"));
        directory(new File(root, "templates"));
        ensure(customersFile, CUSTOMER_HEADER);
        ensure(jobsFile, JOB_HEADER);
        ensure(catalogFile, CATALOG_HEADER);
        ensure(expensesFile, EXPENSE_HEADER);
    }

    public File root() { return root; }

    private static void directory(File target) throws IOException {
        if (!target.isDirectory() && !target.mkdirs()) {
            throw new IOException("Cannot create workspace directory");
        }
    }

    private static List<String> row(String... values) {
        return new ArrayList<>(Arrays.asList(values));
    }

    private static List<List<String>> emptyTable(String[] columns) {
        List<List<String>> result = new ArrayList<>();
        result.add(row(columns));
        return result;
    }

    private static byte[] readBytes(AtomicFile atomic) throws IOException {
        try (InputStream input = atomic.openRead();
             ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
            byte[] chunk = new byte[8192];
            int bytes;
            while ((bytes = input.read(chunk)) != -1) {
                if (buffer.size() + bytes > 16 * 1024 * 1024) {
                    throw new IOException("CSV exceeds bounded read limit");
                }
                buffer.write(chunk, 0, bytes);
            }
            return buffer.toByteArray();
        }
    }

    private static void writeBytes(File file, byte[] contents) throws IOException {
        AtomicFile atomic = new AtomicFile(file);
        FileOutputStream output = null;
        try {
            output = atomic.startWrite();
            output.write(contents);
            atomic.finishWrite(output);
        } catch (IOException | RuntimeException error) {
            if (output != null) atomic.failWrite(output);
            throw error;
        }
    }

    private static void writeText(File file, String text) throws IOException {
        writeBytes(file, text.getBytes(StandardCharsets.UTF_8));
    }

    private static void ensure(File file, String[] header) throws IOException {
        if (!file.isFile() && !new File(file.getPath() + ".bak").exists()) {
            writeRows(file, emptyTable(header));
        }
        table(file, header); // Never silently reset malformed data.
    }

    private static void writeRows(File file, List<List<String>> rows) throws IOException {
        writeText(file, CsvCodec.write(rows));
    }

    private static List<List<String>> table(File file, String[] columns) throws IOException {
        List<List<String>> rows = CsvCodec.read(
            new String(readBytes(new AtomicFile(file)), StandardCharsets.UTF_8)
        );
        if (rows.isEmpty() || !rows.get(0).equals(Arrays.asList(columns))) {
            throw new IOException("Unexpected or missing CSV header: " + file.getName());
        }
        for (List<String> row : rows) {
            if (row.size() != columns.length) {
                throw new IOException("Malformed CSV row: " + file.getName());
            }
        }
        return rows;
    }

    private static String text(String value, boolean required) {
        String trimmed = value == null ? "" : value.trim();
        if (required && trimmed.isEmpty()) throw new IllegalArgumentException("Required field is empty");
        if (trimmed.length() > 250) throw new IllegalArgumentException("Field exceeds 250 characters");
        for (int i=0; i<trimmed.length(); i++) {
            if (Character.isISOControl(trimmed.charAt(i))) {
                throw new IllegalArgumentException("Control characters are not allowed");
            }
        }
        return trimmed;
    }

    private static String id(String prefix) {
        return prefix + UUID.randomUUID().toString().replace("-", "");
    }

    private static String slug(String input) {
        String safe = input.replaceAll("[^A-Za-z0-9_-]+", "_").replaceAll("_+", "_");
        if (safe.isEmpty() || safe.equals("_")) return "Record";
        return safe.length() > 40 ? safe.substring(0, 40) : safe;
    }

    private File guarded(String relative) throws IOException {
        File resolved = new File(root, relative).getCanonicalFile();
        String prefix = root.getCanonicalPath() + File.separator;
        if (!resolved.getPath().startsWith(prefix)) {
            throw new IOException("Workspace traversal rejected");
        }
        return resolved;
    }

    public synchronized List<Customer> customers() throws IOException {
        List<List<String>> rows = table(customersFile, CUSTOMER_HEADER);
        List<Customer> out = new ArrayList<>();
        for (int i=1; i<rows.size(); i++) out.add(new Customer(rows.get(i)));
        return out;
    }

    public synchronized Customer addCustomer(
        String company, String contact, String phone, String email,
        String street, String city, String state, String zip
    ) throws IOException {
        String companyValue = text(company, false);
        String contactValue = text(contact, true);
        String identifier = id("CUST-");
        String folder = "customers/" + identifier + "_" +
            slug(companyValue.isEmpty() ? contactValue : companyValue);
        List<String> columns = row(
            identifier, companyValue, contactValue, text(phone, false), text(email, false),
            text(street, false), text(city, false), text(state, false), text(zip, false), folder
        );
        File clientFolder = guarded(folder);
        directory(clientFolder);
        // Write detail before registering: an interrupted create can leave an orphan,
        // never a master pointer to an uncreated folder.
        writeText(new File(clientFolder, "profile.md"), "# Client notes\n\n");
        List<List<String>> rows = table(customersFile, CUSTOMER_HEADER);
        rows.add(columns);
        writeRows(customersFile, rows);
        return new Customer(columns);
    }

    private Customer customerById(String customerId) throws IOException {
        for (Customer candidate : customers()) {
            if (candidate.id.equals(customerId)) return candidate;
        }
        throw new IOException("Customer not found");
    }

    private File jobFolder(Job job) throws IOException {
        Customer customer = customerById(job.customerId);
        String expected = "customers/" + customer.id + "_";
        if (!customer.folder.startsWith(expected)) {
            throw new IOException("Invalid client folder pointer");
        }
        String subfolder = customer.folder + "/jobs/" + job.id + "_" + slug(job.title);
        return guarded(subfolder);
    }

    public synchronized Job addJob(
        Customer customer, String title, String street, String city,
        String state, String zip, String scheduledDate
    ) throws IOException {
        customerById(customer.id); // Verify foreign key still exists.
        String iso = text(scheduledDate, true);
        try {
            LocalDate.parse(iso);
        } catch (DateTimeParseException error) {
            throw new IllegalArgumentException("Use ISO date YYYY-MM-DD");
        }
        List<String> columns = row(
            id("JOB-"), customer.id, text(title, true), text(street, false),
            text(city, false), text(state, false), text(zip, false), "Scheduled", iso, "0.00"
        );
        Job job = new Job(columns);
        File path = jobFolder(job);
        directory(path);
        writeRows(new File(path, "job_items.csv"), emptyTable(ITEM_HEADER));
        writeText(new File(path, "job_details.json"),
            "{\n  \"schema_version\": 1,\n  \"job_id\": \"" + job.id +
            "\",\n  \"scheduled_date\": \"" + job.date + "\"\n}\n");
        directory(new File(path, "photos"));
        List<List<String>> rows = table(jobsFile, JOB_HEADER);
        rows.add(columns);
        writeRows(jobsFile, rows);
        return job;
    }

    public synchronized List<LineItem> items(Job job) throws IOException {
        File file = new File(jobFolder(job), "job_items.csv");
        List<List<String>> rows = table(file, ITEM_HEADER);
        List<LineItem> out = new ArrayList<>();
        for (int i=1; i<rows.size(); i++) out.add(new LineItem(rows.get(i)));
        return out;
    }

    private BigDecimal totalFor(Job job) throws IOException {
        BigDecimal total = new BigDecimal("0.00");
        for (LineItem line : items(job)) {
            try {
                BigDecimal computed = new BigDecimal(line.quantity)
                    .multiply(new BigDecimal(line.unitRate)).setScale(2, RoundingMode.HALF_UP);
                BigDecimal recorded = new BigDecimal(line.amount).setScale(2, RoundingMode.UNNECESSARY);
                if (computed.compareTo(recorded) != 0) throw new IOException("Corrupted line total");
                total = total.add(recorded);
            } catch (NumberFormatException | ArithmeticException ex) {
                throw new IOException("Invalid monetary amount", ex);
            }
        }
        return total;
    }

    public synchronized List<Job> jobs() throws IOException {
        List<List<String>> rows = table(jobsFile, JOB_HEADER);
        List<Job> result = new ArrayList<>();
        boolean changed = false;
        for (int i=1; i<rows.size(); i++) {
            List<String> r = rows.get(i);
            Job job = new Job(r);
            String computed = totalFor(job).setScale(2, RoundingMode.HALF_UP).toPlainString();
            if (!r.get(9).equals(computed)) {
                r.set(9, computed);
                changed = true;
            }
            result.add(new Job(r));
        }
        if (changed) writeRows(jobsFile, rows);
        result.sort(Comparator.comparing((Job j) -> j.date).thenComparing(j -> j.id));
        return result;
    }

    public synchronized LineItem addLine(Job job, String description, String quantity, String unitRate)
        throws IOException {
        String label = text(description, true);
        BigDecimal q;
        BigDecimal rate;
        try {
            q = new BigDecimal(text(quantity, true));
            rate = new BigDecimal(text(unitRate, true));
        } catch (NumberFormatException error) {
            throw new IllegalArgumentException("Quantity and rate must be numbers");
        }
        if (q.signum() <= 0 || q.compareTo(new BigDecimal("1000000")) > 0 ||
            q.scale() > 4 || rate.abs().compareTo(new BigDecimal("1000000")) > 0 ||
            rate.scale() > 2) {
            throw new IllegalArgumentException("Invalid quantity or rate precision");
        }
        if (rate.signum() < 0 && !label.toLowerCase(Locale.ROOT).contains("discount")) {
            throw new IllegalArgumentException("Negative rates require a discount description");
        }
        Job known = null;
        for (Job current : jobs()) {
            if (current.id.equals(job.id)) known = current;
        }
        if (known == null) throw new IOException("Job not found");
        String lineId = id(rate.signum() < 0 ? "DISC-" : "CUSTOM-");
        BigDecimal amount = q.multiply(rate).setScale(2, RoundingMode.HALF_UP);
        List<String> columns = row(lineId, label, q.toPlainString(),
            rate.setScale(2, RoundingMode.HALF_UP).toPlainString(), amount.toPlainString());
        File file = new File(jobFolder(known), "job_items.csv");
        List<List<String>> rows = table(file, ITEM_HEADER);
        rows.add(columns);
        writeRows(file, rows);
        // Repairable index: if process stops here jobs() fixes cached totals on next read.
        jobs();
        return new LineItem(columns);
    }


    /** Customer records remain addressable by stable ID; folder paths are not renamed. */
    public synchronized Customer updateCustomer(
        String customerId, String company, String contact, String phone, String email,
        String street, String city, String state, String zip
    ) throws IOException {
        List<List<String>> rows = table(customersFile, CUSTOMER_HEADER);
        for (int i = 1; i < rows.size(); i++) {
            List<String> r = rows.get(i);
            if (r.get(0).equals(customerId)) {
                List<String> next = row(customerId, text(company, false), text(contact, true),
                    text(phone, false), text(email, false), text(street, false),
                    text(city, false), text(state, false), text(zip, false), r.get(9));
                rows.set(i, next);
                writeRows(customersFile, rows);
                return new Customer(next);
            }
        }
        throw new IOException("Customer not found; no changes saved");
    }

    /** Update the canonical jobs index in one AtomicFile commit. */
    public synchronized Job updateJob(String jobId, String scheduledDate, String status)
        throws IOException {
        String date = text(scheduledDate, true);
        try { LocalDate.parse(date); }
        catch (DateTimeParseException error) {
            throw new IllegalArgumentException("Choose a valid calendar date");
        }
        String nextStatus = text(status, true);
        if (!Arrays.asList("Scheduled", "In Progress", "On Hold", "Completed", "Cancelled")
            .contains(nextStatus)) throw new IllegalArgumentException("Unknown job status");
        List<List<String>> rows = table(jobsFile, JOB_HEADER);
        for (int i = 1; i < rows.size(); i++) {
            List<String> r = rows.get(i);
            if (r.get(0).equals(jobId)) {
                r.set(7, nextStatus);
                r.set(8, date);
                writeRows(jobsFile, rows);
                return new Job(r);
            }
        }
        throw new IOException("Job not found; no changes saved");
    }

    /** Replace a line item atomically; cached job totals are safely recalculated. */
    public synchronized void updateLine(Job job, String lineId, String description,
                                        String quantity, String unitRate) throws IOException {
        List<List<String>> rows = table(new File(jobFolder(job), "job_items.csv"), ITEM_HEADER);
        for (int i = 1; i < rows.size(); i++) {
            if (rows.get(i).get(0).equals(lineId)) {
                BigDecimal q, rate;
                try {
                    q = new BigDecimal(text(quantity, true));
                    rate = new BigDecimal(text(unitRate, true));
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("Quantity and rate must be numeric");
                }
                String desc = text(description, true);
                if (q.signum() <= 0 || q.compareTo(new BigDecimal("1000000")) > 0
                    || q.scale() > 4 || rate.scale() > 2
                    || rate.abs().compareTo(new BigDecimal("1000000")) > 0
                    || (rate.signum() < 0 && !desc.toLowerCase(Locale.ROOT).contains("discount"))) {
                    throw new IllegalArgumentException("Check quantity, rate or discount description");
                }
                BigDecimal amount = q.multiply(rate).setScale(2, RoundingMode.HALF_UP);
                rows.set(i, row(lineId, desc, q.toPlainString(),
                    rate.setScale(2, RoundingMode.HALF_UP).toPlainString(),
                    amount.toPlainString()));
                writeRows(new File(jobFolder(job), "job_items.csv"), rows);
                jobs();
                return;
            }
        }
        throw new IOException("Line item not found");
    }

    public synchronized void deleteLine(Job job, String lineId) throws IOException {
        File file = new File(jobFolder(job), "job_items.csv");
        List<List<String>> rows = table(file, ITEM_HEADER);
        boolean removed = rows.removeIf(r -> r.size() > 0 && r.get(0).equals(lineId));
        if (!removed) throw new IOException("Line item not found");
        writeRows(file, rows);
        jobs();
    }

    /** Explicit user-selected image import; bounded copy; no media/storage permissions. */
    public synchronized String addPhoto(Job job, InputStream source) throws IOException {
        if (source == null) throw new IOException("Photo selection cannot be opened");
        BufferedInputStream input = new BufferedInputStream(source);
        input.mark(16);
        byte[] magic = new byte[12];
        int count = 0;
        while (count < magic.length) {
            int got = input.read(magic, count, magic.length - count);
            if (got < 0) break;
            count += got;
        }
        input.reset();
        String ext;
        if (count >= 3 && (magic[0] & 255) == 0xff
            && (magic[1] & 255) == 0xd8 && (magic[2] & 255) == 0xff) ext = ".jpg";
        else if (count >= 8 && (magic[0] & 255) == 137 && magic[1] == 80
            && magic[2] == 78 && magic[3] == 71) ext = ".png";
        else if (count >= 12 && magic[0] == 'R' && magic[1] == 'I'
            && magic[2] == 'F' && magic[3] == 'F'
            && magic[8] == 'W' && magic[9] == 'E'
            && magic[10] == 'B' && magic[11] == 'P') ext = ".webp";
        else throw new IOException("Select a JPEG, PNG or WebP photo");
        File photos = new File(jobFolder(job), "photos");
        directory(photos);
        String name = id("PHOTO-") + ext;
        File output = new File(photos, name);
        AtomicFile atomic = new AtomicFile(output);
        FileOutputStream dest = null;
        try {
            dest = atomic.startWrite();
            int total = 0;
            byte[] buffer = new byte[8192];
            int size;
            while ((size = input.read(buffer)) != -1) {
                total += size;
                if (total > 25 * 1024 * 1024) throw new IOException("Photo exceeds 25 MB");
                dest.write(buffer, 0, size);
            }
            atomic.finishWrite(dest);
        } catch (IOException | RuntimeException e) {
            if (dest != null) atomic.failWrite(dest);
            throw e;
        }
        return name;
    }

    public synchronized List<String> photos(Job job) throws IOException {
        File folder = new File(jobFolder(job), "photos");
        directory(folder);
        File[] files = folder.listFiles();
        if (files == null) throw new IOException("Photo directory unreadable");
        List<String> names = new ArrayList<>();
        for (File f : files) {
            if (f.isFile() && f.getName().matches("PHOTO-[a-f0-9]{32}\\.(jpg|png|webp)")) {
                names.add(f.getName());
            }
        }
        names.sort(String::compareTo);
        return names;
    }

    public synchronized File photoFile(Job job, String name) throws IOException {
        if (!name.matches("PHOTO-[a-f0-9]{32}\\.(jpg|png|webp)")) {
            throw new IOException("Invalid photo reference");
        }
        File file = new File(new File(jobFolder(job), "photos"), name);
        if (!file.isFile() || java.nio.file.Files.isSymbolicLink(file.toPath())) {
            throw new IOException("Photo not found");
        }
        return file;
    }

    public synchronized void deletePhoto(Job job, String name) throws IOException {
        File file = photoFile(job, name);
        if (!file.delete()) throw new IOException("Cannot delete photo");
    }

    /** Explicit restore, never called without owner choosing a ZIP via system picker. */
    public synchronized void restoreBackup(InputStream selectedZip) throws IOException {
        BackupArchive.restore(root, selectedZip);
        // Don't claim success until the activated workspace can be fully reopened.
        BackupArchive.validate(root);
    }

    public synchronized boolean hasRollbackSnapshot() {
        return BackupArchive.rollback(root).isDirectory();
    }

    public synchronized void discardRollbackSnapshot() throws IOException {
        BackupArchive.clearPreviousSnapshot(root);
    }

    public synchronized void exportBackup(OutputStream destination) throws IOException {
        jobs(); // Reconcile denormalized totals before snapshotting.
        try (ZipOutputStream zip = new ZipOutputStream(destination, StandardCharsets.UTF_8)) {
            zipEntries(zip, root, root);
            zip.finish();
        }
    }

    private static void zipEntries(ZipOutputStream zip, File root, File current) throws IOException {
        File[] entries = current.listFiles();
        if (entries == null) throw new IOException("Workspace directory is unreadable");
        Arrays.sort(entries, Comparator.comparing(File::getName));
        for (File entry : entries) {
            if (java.nio.file.Files.isSymbolicLink(entry.toPath())) {
                throw new IOException("Backup refuses symbolic links");
            }
            String relative = root.toPath().relativize(entry.toPath()).toString()
                .replace(File.separatorChar, '/');
            if (relative.endsWith(".new") || relative.endsWith(".bak")) continue;
            if (entry.isDirectory()) {
                zipEntries(zip, root, entry);
            } else if (entry.isFile()) {
                zip.putNextEntry(new ZipEntry(relative));
                try (InputStream input = new FileInputStream(entry)) {
                    byte[] buffer = new byte[8192];
                    int size;
                    while ((size = input.read(buffer)) != -1) zip.write(buffer, 0, size);
                }
                zip.closeEntry();
            } else {
                throw new IOException("Backup contains unknown file type");
            }
        }
    }
}
