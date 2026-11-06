package com.accubook.crm;

import java.util.List;

/** Portable, script-free, network-free HTML export; not a receipt or tax document. */
public final class InvoiceHtml {
    private InvoiceHtml() {}

    private static String esc(String input) {
        return (input == null ? "" : input)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\"", "&quot;")
            .replace("'", "&#39;");
    }

    public static String render(WorkspaceStore.Customer customer, WorkspaceStore.Job job,
                                List<WorkspaceStore.LineItem> items) {
        StringBuilder html = new StringBuilder();
        html.append("<!doctype html><html lang=\"en\"><head><meta charset=\"UTF-8\">")
            .append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">")
            .append("<title>Accubook draft ").append(esc(job.id)).append("</title><style>")
            .append("body{font-family:system-ui,Arial,sans-serif;max-width:850px;margin:2rem auto;")
            .append("padding:0 1rem;color:#1b263b}table{width:100%;border-collapse:collapse}")
            .append("th,td{padding:.8rem;border-bottom:1px solid #cad2dd;text-align:left}")
            .append("th{background:#eef3f9}td:last-child,th:last-child{text-align:right}")
            .append(".total{text-align:right;font-size:1.4rem;font-weight:bold}")
            .append("@media print{body{margin:0}}")
            .append("</style></head><body>")
            .append("<h1>Accubook — Draft invoice</h1>")
            .append("<p><strong>Draft — review before sending. Not proof of payment.</strong></p>")
            .append("<p><strong>Customer:</strong> ").append(esc(customer.displayName()))
            .append("<br><strong>Billing:</strong> ").append(esc(customer.street))
            .append(", ").append(esc(customer.city)).append(", ").append(esc(customer.state))
            .append(" ").append(esc(customer.zip)).append("</p>")
            .append("<p><strong>Service:</strong> ").append(esc(job.title))
            .append("<br><strong>Site:</strong> ").append(esc(job.street))
            .append(", ").append(esc(job.city)).append(", ").append(esc(job.state))
            .append(" ").append(esc(job.zip))
            .append("<br><strong>Scheduled:</strong> ").append(esc(job.date))
            .append("<br><strong>Job reference:</strong> ").append(esc(job.id)).append("</p>")
            .append("<table><caption>Itemized work</caption><thead><tr>")
            .append("<th scope=\"col\">Description</th><th scope=\"col\">Quantity</th>")
            .append("<th scope=\"col\">Unit rate</th><th scope=\"col\">Amount</th>")
            .append("</tr></thead><tbody>");
        for (WorkspaceStore.LineItem line : items) {
            html.append("<tr><td>").append(esc(line.description))
                .append("</td><td>").append(esc(line.quantity))
                .append("</td><td>$").append(esc(line.unitRate))
                .append("</td><td>$").append(esc(line.amount)).append("</td></tr>");
        }
        html.append("</tbody></table><p class=\"total\">Total: $")
            .append(esc(job.total)).append("</p>")
            .append("<p>Tax, payment terms, invoice numbering, and payment settlement ")
            .append("are not configured in this development build.</p></body></html>");
        return html.toString();
    }
}
