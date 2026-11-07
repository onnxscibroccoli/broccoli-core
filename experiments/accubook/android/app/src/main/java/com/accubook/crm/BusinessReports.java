package com.accubook.crm;

import java.io.IOException;
import java.io.OutputStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * Human-readable, user-scoped accounting extracts for manual CSV import/mapping.
 * Not direct QuickBooks authentication, tax preparation or settlement reconciliation.
 * Never sends records to a network or payment provider.
 */
public final class BusinessReports {
    public static final String[] SECTIONS={
        "Customers (contact information)",
        "Jobs and invoice totals",
        "Estimate / invoice line items",
        "Manual payments by method",
        "Expenses and tax-cost categories",
        "Worker time entries"
    };
    private BusinessReports(){}

    private static List<String> r(String... values){
        return new ArrayList<>(Arrays.asList(values));
    }
    private static void put(ZipOutputStream zip,String name,List<List<String>> rows) throws IOException{
        zip.putNextEntry(new ZipEntry(name));
        byte[] utf8=CsvCodec.write(rows).getBytes(StandardCharsets.UTF_8);
        zip.write(utf8);
        zip.closeEntry();
    }
    /** Preexisting call signature: explicit all-category compatibility for older callers. */
    public static void export(WorkspaceStore store,CrmWorkspace crm,
                              boolean[] sections,OutputStream destination) throws IOException {
        Set<String> allCategories=new LinkedHashSet<>();
        for(CrmWorkspace.Expense item:crm.expenses())allCategories.add(item.category);
        // A legacy expense request with no expenses still creates a headers-only CSV.
        // The new selector requires one category only when there are records to filter.
        if(allCategories.isEmpty())allCategories.add("(no expenses)");
        export(store,crm,ExportSelection.legacy(sections,allCategories),destination);
    }

    public static void export(WorkspaceStore store,CrmWorkspace crm,
                              ExportSelection selection,OutputStream destination)
        throws IOException {
        boolean[] sections=selection.sections;
        try(ZipOutputStream zip=new ZipOutputStream(destination,StandardCharsets.UTF_8)){
            List<WorkspaceStore.Customer> customers=store.customers();
            List<WorkspaceStore.Job> jobs=store.jobs();
            if(sections[0]){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("CustomerID","CompanyName","ContactName","Phone","Email",
                    "BillingStreet","BillingCity","BillingState","BillingZip"));
                for(WorkspaceStore.Customer c:customers)
                    rows.add(r(c.id,c.company,c.contact,c.phone,c.email,c.street,
                        c.city,c.state,c.zip));
                put(zip,"customers.csv",rows);
            }
            if(sections[1]){
                List<List<String>> rows=new ArrayList<>();
                List<String> header=r("DocumentReference","CustomerID","ServiceDate",
                    "JobTitle","JobStatus","DraftAmount");
                if(sections[3]){
                    header.add("SelectedPaymentReceipts");
                    header.add("BalanceAfterSelectedPayments");
                }
                rows.add(header);
                for(WorkspaceStore.Job j:jobs){
                    List<String> record=r(DocumentNumbers.reference(j.id,j.date,false),
                        j.customerId,j.date,j.title,j.status,j.total);
                    // Excluded payment methods must not leak via job-level rollups.
                    if(sections[3]){
                        BigDecimal selected=ReportPrivacy.selectedReceipts(
                            crm.payments(j),selection.paymentMethods,
                            p->p.method,p->p.amount);
                        record.add(selected.toPlainString());
                        record.add(new BigDecimal(j.total).subtract(selected).toPlainString());
                    }
                    rows.add(record);
                }
                put(zip,"jobs_and_invoices.csv",rows);
            }
            if(sections[2]){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("DocumentReference","CustomerID","ServiceDate","Description",
                    "Quantity","UnitRate","LineTotal"));
                for(WorkspaceStore.Job j:jobs)
                    for(WorkspaceStore.LineItem line:store.items(j))
                        rows.add(r(DocumentNumbers.reference(j.id,j.date,false),j.customerId,
                            j.date,line.description,line.quantity,line.unitRate,line.amount));
                put(zip,"invoice_lines.csv",rows);
            }
            if(sections[3]){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("PaymentDate","DocumentReference","CustomerID","PaymentMethod",
                    "Amount","Reference","Notes"));
                for(WorkspaceStore.Job j:jobs)
                    for(CrmWorkspace.Payment payment:crm.payments(j))
                        if(selection.includesPayment(payment.method))rows.add(r(payment.date,DocumentNumbers.reference(j.id,j.date,false),
                            j.customerId,payment.method,payment.amount,payment.reference,payment.note));
                put(zip,"payments_by_method.csv",rows);
            }
            if(sections[4]){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("Date","Description","Amount","Category"));
                for(CrmWorkspace.Expense e:crm.expenses())
                    if(selection.includesExpense(e.category))rows.add(r(e.date,e.description,e.amount,e.category));
                put(zip,"expenses_quickbooks_mapping.csv",rows);
            }
            if(sections[5]){
                List<List<String>> rows=new ArrayList<>();
                rows.add(r("DocumentReference","Worker","ClockInUTC","ClockOutUTC",
                    "HoursDecimal","WorkNotes"));
                for(WorkspaceStore.Job j:jobs)
                    for(CrmWorkspace.TimeEntry time:crm.timeEntries(j))
                        rows.add(r(DocumentNumbers.reference(j.id,j.date,false),time.worker,
                            time.start,time.end,time.hours,time.note));
                put(zip,"worker_hours.csv",rows);
            }
            zip.putNextEntry(new ZipEntry("EXPORT_SCOPE.txt"));
            StringBuilder scope=new StringBuilder("Explicit export scope. Files not selected are not included.\\n");
            for(int i=0;i<SECTIONS.length;i++)
                scope.append(sections[i]?"INCLUDED: ":"EXCLUDED: ").append(SECTIONS[i]).append('\\n');
            scope.append("Included payment methods: ").append(selection.paymentMethods).append('\\n')
                .append("Included expense categories: ").append(selection.expenseCategories).append('\\n');
            zip.write(scope.toString().getBytes(StandardCharsets.UTF_8));
            zip.closeEntry();

            zip.putNextEntry(new ZipEntry("README_IMPORT.txt"));
            String doc="Accubook optional accounting export. All values are local manual records.\n"
                +"No online account connection, provider settlement or tax calculation occurred.\n"
                +"Import only selected CSV files; inspect and map each field in your accounting software.\n"
                +"QuickBooks Online import schemas differ by region, account and import screen.\n"
                +"Expense CSV uses Date, Description, Amount, Category; verify transaction signs\n"
                +"and category/tax mappings before any real financial import.\n"
                +"Draft invoices are not legally issued numbered invoices or proof of payment.\n"
                +"Customer and worker details may be sensitive. Secure the exported ZIP.\n"
                +"Route/precise location records are intentionally excluded.\n";
            zip.write(doc.getBytes(StandardCharsets.UTF_8));
            zip.closeEntry();
            zip.finish();
        }
    }
}
