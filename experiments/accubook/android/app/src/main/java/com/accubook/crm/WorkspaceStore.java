package com.accubook.crm;

import android.content.Context;
import android.util.AtomicFile;

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
