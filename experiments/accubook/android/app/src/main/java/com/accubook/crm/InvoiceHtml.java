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
            .append("<title>Accubook Invoice ").append(esc(DocumentNumbers.reference(job.id,job.date,false))).append("</title><style>")
            .append("body{font-family:system-ui,Arial,sans-serif;max-width:850px;margin:2rem auto;")
            .append("padding:0 1rem;color:#1b263b}table{width:100%;border-collapse:collapse}")
            .append("th,td{padding:.8rem;border-bottom:1px solid #cad2dd;text-align:left}")
            .append("th{background:#eef3f9}td:last-child,th:last-child{text-align:right}")
            .append(".total{text-align:right;font-size:1.4rem;font-weight:bold}")
            .append("@media print{body{margin:0}}")
            .append("</style></head><body>")
            .append("<h1>Accubook — Invoice</h1>")
            .append("<p><strong>Review before sending. Not proof of payment.</strong></p>")
            .append("<p><strong>Customer:</strong> ").append(esc(customer.displayName()))
            .append("<br><strong>Billing:</strong> ").append(esc(customer.street))
            .append(", ").append(esc(customer.city)).append(", ").append(esc(customer.state))
            .append(" ").append(esc(customer.zip)).append("</p>")
            .append("<p><strong>Service:</strong> ").append(esc(job.title))
            .append("<br><strong>Site:</strong> ").append(esc(job.street))
            .append(", ").append(esc(job.city)).append(", ").append(esc(job.state))
            .append(" ").append(esc(job.zip))
            .append("<br><strong>Scheduled:</strong> ").append(esc(job.date))
            .append("<br><strong>Reference:</strong> ").append(esc(DocumentNumbers.reference(job.id,job.date,false))).append("</p>")
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
    /** Only presentation tags with no attributes survive an editable rich-text round trip. */
    public static String safeRichFragment(String fragment) {
        if(fragment==null)return "";
        StringBuilder output=new StringBuilder();
        java.util.regex.Matcher matcher=java.util.regex.Pattern.compile("<[^>]*>|[^<]+|<").matcher(fragment);
        while(matcher.find()) {
            String part=matcher.group();
            if(part.startsWith("<") && part.endsWith(">")) {
                String tag=part.substring(1,part.length()-1).trim()
                    .toLowerCase(java.util.Locale.ROOT);
                if(tag.matches("/?(b|strong|i|em|u|br|p|div|ul|li|h2)")) {
                    output.append("<").append(tag).append(">");
                }
            } else {
                // Preserve the five canonical HTML entities; escape all other ampersands.
                output.append(part.replaceAll("&(?!(amp|lt|gt|quot|#39);)", "&amp;")
                    .replace(">", "&gt;").replace("\r", "").replace("\n", "<br>"));
            }
        }
        return output.toString();
    }

    /** The invoice/quote preview is also the printable layout (offline, inline resources). */
    public static String renderDocument(WorkspaceStore.Customer customer, WorkspaceStore.Job job,
                                        java.util.List<WorkspaceStore.LineItem> lines,
                                        CrmWorkspace.Branding brand, CrmWorkspace.Memo memo,
                                        byte[] logoBytes, boolean quote, boolean editable) {
        String type=quote?"ESTIMATE":"INVOICE";
        String edit=editable?" contenteditable=\"true\" spellcheck=\"true\"":"";
        StringBuilder html=new StringBuilder();
        html.append("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
            .append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
            .append("<style>:root{--accent:").append(esc(brand.accent))
            .append("}*{box-sizing:border-box}body{font-family:system-ui,Roboto,Arial,sans-serif;")
            .append("margin:0;background:#e9edf4;color:#172435}.paper{background:white;")
            .append("max-width:816px;margin:0 auto;min-height:1050px;padding:32px 34px}")
            .append(".top{display:flex;justify-content:space-between;align-items:start;gap:16px}")
            .append(".brand{max-width:60%}.brand img{max-height:100px;max-width:220px;")
            .append("object-fit:contain}h1{font-size:26px;margin:0 0 6px;color:var(--accent)}")
            .append(".meta{margin-top:20px;display:grid;grid-template-columns:1fr 1fr;gap:16px}")
            .append("h2{font-size:16px;border-bottom:2px solid var(--accent);padding-bottom:8px}")
            .append("p{line-height:1.6}table{border-collapse:collapse;width:100%;margin:20px 0}")
            .append("th,td{padding:10px;border-bottom:1px solid #d7e0eb;text-align:left}")
            .append("th{background:#f0f4fa}td:last-child,th:last-child{text-align:right}")
            .append(".total{font-weight:bold;font-size:20px;text-align:right;margin-top:18px}")
            .append(".rich{min-height:58px;white-space:normal;line-height:1.5;padding:12px;")
            .append("border:1px solid transparent}.rich[contenteditable]{border:2px dashed ")
            .append("var(--accent);border-radius:7px;background:#f5f9ff}")
            .append(".fine{color:#445468;font-size:13px}address{font-style:normal}")
            .append("@media(max-width:640px){.paper{padding:20px 16px}.meta{grid-template-columns:1fr}")
            .append(".brand{max-width:62%}th,td{padding:6px;font-size:12px}}")
            .append("@media print{body{background:white}.paper{padding:0;min-height:auto;")
            .append("max-width:none}.rich[contenteditable]{border:0;background:white}")
            .append("@page{size:auto;margin:14mm}}</style></head><body><main class='paper'>")
            .append("<header class='top'><div class='brand'>");
        if(logoBytes!=null && logoBytes.length>0 &&
            (brand.logoMime.equals("image/png")||brand.logoMime.equals("image/jpeg")||
                brand.logoMime.equals("image/webp"))) {
            html.append("<img alt='Business logo' src='data:")
                .append(brand.logoMime).append(";base64,")
                .append(java.util.Base64.getEncoder().encodeToString(logoBytes)).append("'>");
        }
        html.append("<h1>").append(esc(brand.business)).append("</h1><address>")
            .append(esc(brand.address).replace("\n","<br>")).append("</address><p>")
            .append(esc(brand.phone)).append("<br>").append(esc(brand.email))
            .append("</p></div><div><h1>").append(type).append("</h1>")
            .append("<p class='fine'>").append(quote?"Estimate · approval required":"Invoice · not a receipt")
            .append("<br>Document: ").append(esc(DocumentNumbers.reference(job.id,job.date,quote))).append("</p></div></header>")
            .append("<div class='meta'><section><h2>Prepared for</h2>")
            .append("<strong>").append(esc(customer.displayName())).append("</strong><br>")
            .append(esc(customer.street)).append("<br>").append(esc(customer.city))
            .append(", ").append(esc(customer.state)).append(" ").append(esc(customer.zip))
            .append("<br>").append(esc(customer.phone)).append("</section>")
            .append("<section><h2>Service</h2><strong>").append(esc(job.title))
            .append("</strong><br>Scheduled: ").append(esc(job.date))
            .append("<br>Site: ").append(esc(job.street)).append(", ").append(esc(job.city))
            .append(", ").append(esc(job.state)).append(" ").append(esc(job.zip))
            .append("</section></div><section aria-label='Editable message'>")
            .append("<h2>Message</h2><div id='greeting' class='rich'").append(edit).append(">")
            .append(safeRichFragment(memo.greeting)).append("</div></section>")
            .append("<section><h2>").append(quote?"Proposed work":"Itemized work").append("</h2>")
            .append("<table><thead><tr><th scope='col'>Description</th><th scope='col'>Qty</th>")
            .append("<th scope='col'>Unit rate</th><th scope='col'>Amount</th></tr></thead><tbody>");
        for(WorkspaceStore.LineItem line:lines) {
            html.append("<tr><td>").append(esc(line.description)).append("</td><td>")
                .append(esc(line.quantity)).append("</td><td>$")
                .append(esc(line.unitRate)).append("</td><td>$")
                .append(esc(line.amount)).append("</td></tr>");
        }
        html.append("</tbody></table><div class='total'>")
            .append(quote?"Estimated total: $":"Invoice total: $").append(esc(job.total))
            .append("</div></section><section><h2>Terms</h2><p>")
            .append(esc(brand.terms).replace("\n","<br>"))
            .append("</p><div id='closing' class='rich'").append(edit).append(">")
            .append(safeRichFragment(memo.closing)).append("</div></section>")
            .append("<footer class='fine'><p>").append(esc(brand.footer))
            .append("</p><p>Generated locally with Accubook. ")
            .append(quote?"Estimate is not an invoice.":"Invoice is not proof of payment.")
            .append("</p></footer></main></body></html>");
        return html.toString();
    }

}
