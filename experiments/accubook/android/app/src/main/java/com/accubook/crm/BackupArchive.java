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
    private static final String[] CATALOG = {"ItemID", "Category", "ItemName", "DefaultUnit", "DefaultRate"};
    private static final String[] EXPENSE = {"ExpenseID", "Date", "Category", "Description", "Amount"};

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
        if (name.matches("templates/[A-Za-z0-9_./-]{1,220}\\.(html|txt|md|json)"))
            return !name.contains("..");
        String client = "customers/CUST-[a-f0-9]{32}_[A-Za-z0-9_-]{1,40}";
        if (name.matches(client + "/profile\\.md")) return true;
        String job = client + "/jobs/JOB-[a-f0-9]{32}_[A-Za-z0-9_-]{1,40}";
        return name.matches(job + "/(job_items\\.csv|job_details\\.json|photos/PHOTO-[a-f0-9]{32}\\.(jpg|png|webp))");
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
                long perFile = name.contains("/photos/") ? LIMIT_PHOTO : LIMIT_OTHER;
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
