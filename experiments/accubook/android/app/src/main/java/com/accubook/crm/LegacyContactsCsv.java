package com.accubook.crm;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Strict offline, contact-only CRM CSV migration preview.
 * Does not mutate a workspace or create a customer. Column mapping is always
 * visible and user-confirmed; guesses are conveniences, not silent imports.
 */
public final class LegacyContactsCsv {
    public static final int MAX_BYTES=2*1024*1024, MAX_ROWS=5000, MAX_COLUMNS=64;
    public static final class Entry {
        public final String source,name,phone,email;
        public Entry(String id,String person,String telephone,String mail){
            source=id;name=person;phone=telephone;email=mail;
        }
    }
    public static final class Preview {
        public final List<Entry> entries;
        public final int sourceRows,skipped;
        Preview(List<Entry> rows,int count,int removed){
            entries=Collections.unmodifiableList(rows);
            sourceRows=count;skipped=removed;
        }
    }
    private final List<String> headers;
    private final List<List<String>> rows;
    private final String fingerprint;
    private LegacyContactsCsv(List<String> headers,List<List<String>> rows,String fingerprint){
        this.headers=Collections.unmodifiableList(new ArrayList<>(headers));
        this.rows=rows;this.fingerprint=fingerprint;
    }
    public List<String> headers(){return headers;}
    public int count(){return rows.size();}
    private static String normalized(String column){
        return column.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]","");
    }
    private static final Set<String> NAME_ALIASES=new HashSet<>(Arrays.asList(
        "name","fullname","contact","contactname","customername","clientname",
        "companyname","businessname","displayname"));
    private static final Set<String> PHONE_ALIASES=new HashSet<>(Arrays.asList(
        "phone","phonenumber","telephone","mobile","mobilenumber","cell",
        "cellphone","primaryphone"));
    private static final Set<String> EMAIL_ALIASES=new HashSet<>(Arrays.asList(
        "email","emailaddress","mail","primaryemail","contactemail"));
    /** -1 means no unambiguous match: a person must select the destination. */
    public int guess(String target){
        Set<String> aliases;
        switch(target){
            case "name": aliases=NAME_ALIASES;break;
            case "phone": aliases=PHONE_ALIASES;break;
            case "email": aliases=EMAIL_ALIASES;break;
            default:throw new IllegalArgumentException("Unknown contact column");
        }
        int found=-1;
        for(int i=0;i<headers.size();i++){
            if(aliases.contains(normalized(headers.get(i)))){
                if(found>=0)return -1;
                found=i;
            }
        }
        return found;
    }
    private static String fingerprint(String csv) throws IOException {
        try{
            byte[] hash=MessageDigest.getInstance("SHA-256")
                .digest(csv.getBytes(StandardCharsets.UTF_8));
            StringBuilder value=new StringBuilder("csv:");
            for(int i=0;i<12;i++)value.append(String.format(Locale.ROOT,"%02x",hash[i]&255));
            return value.toString();
        }catch(java.security.NoSuchAlgorithmException error){
            throw new IOException("SHA-256 unavailable",error);
        }
    }
    public static LegacyContactsCsv parse(String csv) throws IOException {
        if(csv==null||csv.getBytes(StandardCharsets.UTF_8).length>MAX_BYTES)
            throw new IOException("Select a CSV under 2 MB");
        List<List<String>> data=CsvCodec.read(csv);
        if(data.size()<2)throw new IOException("CSV needs a header and at least one record");
        List<String> header=data.get(0);
        if(header.size()<1||header.size()>MAX_COLUMNS)
            throw new IOException("Unsupported CSV column count");
        if(data.size()-1>MAX_ROWS)
            throw new IOException("Import up to 5000 contacts at a time");
        Set<String> named=new HashSet<>();
        for(String h:header){
            String normalized=normalized(h);
            if(normalized.isEmpty()||!named.add(normalized))
                throw new IOException("Blank or repeated column heading");
            if(h.length()>120)throw new IOException("Column heading is too long");
        }
        List<List<String>> records=new ArrayList<>();
        for(int i=1;i<data.size();i++){
            if(data.get(i).size()!=header.size())
                throw new IOException("CSV row "+(i+1)+" has a different column count");
            records.add(new ArrayList<>(data.get(i)));
        }
        return new LegacyContactsCsv(header,records,fingerprint(csv));
    }
    private String read(List<String> row,int column,int max) throws IOException {
        if(column<0)return "";
        String value=row.get(column).trim();
        if(value.length()>max||value.indexOf('\0')>=0||
            value.indexOf('\n')>=0||value.indexOf('\r')>=0)
            throw new IOException("Contact field is too long or has multiple lines");
        return value;
    }
    /** Columns index the CSV header; -1 is allowed only for phone/email. */
    public Preview preview(int nameColumn,int phoneColumn,int emailColumn) throws IOException {
        if(nameColumn<0||nameColumn>=headers.size())throw new IOException("Choose a Name column");
        if(phoneColumn>=headers.size()||emailColumn>=headers.size()||
            phoneColumn < -1||emailColumn < -1)
            throw new IOException("Unknown selected CSV column");
        if(nameColumn==phoneColumn||nameColumn==emailColumn||
            (phoneColumn>=0&&phoneColumn==emailColumn))
            throw new IOException("A CSV column cannot map to two fields");
        List<Entry> result=new ArrayList<>();
        int skipped=0;
        for(int i=0;i<rows.size();i++){
            List<String> row=rows.get(i);
            String name=read(row,nameColumn,180);
            String phone=read(row,phoneColumn,80);
            String email=read(row,emailColumn,160);
            if(name.isEmpty()){skipped++;continue;}
            result.add(new Entry(fingerprint+":"+(i+1),name,phone,email));
        }
        if(result.isEmpty())throw new IOException("No named contacts match that mapping");
        return new Preview(result,rows.size(),skipped);
    }
}
