package com.accubook.crm;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.List;

/**
 * Canonical, portable change-order calculations and integrity proofs.
 * SHA-256 detects accidental/unapproved edits; it is NOT a digital signature
 * or proof of identity because a person with workspace write access can
 * regenerate hashes. No network or key custody is required.
 */
public final class ChangeOrderProof {
    private ChangeOrderProof() {}

    public static String sha256(byte[] bytes) {
        try {
            byte[] digest=MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder out=new StringBuilder(64);
            for(byte b:digest) out.append(String.format(java.util.Locale.ROOT,"%02x",b&255));
            return out.toString();
        } catch(NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable",e);
        }
    }
    private static void part(StringBuilder out,String text) {
        String value=text==null?"":text;
        out.append(value.getBytes(StandardCharsets.UTF_8).length).append(':').append(value);
    }
    /** Lines have exactly ID, OrderID, Description, Quantity, Rate, Amount. */
    public static String contentHash(String jobId,String orderId,String title,
            String acknowledgedUtc,String signedBy,String signatureSha,
            List<List<String>> lines) {
        StringBuilder data=new StringBuilder("ACCU-CHANGE-ORDER-V1\n");
        for(String s:new String[]{jobId,orderId,title,acknowledgedUtc,signedBy,signatureSha})
            part(data,s);
        part(data,Integer.toString(lines.size()));
        for(List<String> line:lines) {
            if(line.size()!=6 || !orderId.equals(line.get(1)))
                throw new IllegalArgumentException("Invalid change-order line");
            for(String s:line)part(data,s);
        }
        return sha256(data.toString().getBytes(StandardCharsets.UTF_8));
    }
    public static String amount(String quantity,String price) {
        try {
            BigDecimal q=new BigDecimal(quantity),p=new BigDecimal(price);
            if(q.signum()<=0 || q.scale()>4 || q.compareTo(new BigDecimal("1000000"))>0
                    || p.scale()>2 || p.abs().compareTo(new BigDecimal("1000000"))>0)
                throw new IllegalArgumentException("Quantity or rate out of range");
            return q.multiply(p).setScale(2,RoundingMode.HALF_UP).toPlainString();
        } catch(NumberFormatException e) {
            throw new IllegalArgumentException("Enter numeric quantity and rate",e);
        }
    }
    public static String total(List<List<String>> lines) {
        BigDecimal sum=BigDecimal.ZERO;
        for(List<String> line:lines) {
            if(line.size()!=6 || !amount(line.get(3),line.get(4)).equals(line.get(5)))
                throw new IllegalArgumentException("Invalid stored change-order amount");
            sum=sum.add(new BigDecimal(line.get(5)));
        }
        return sum.setScale(2,RoundingMode.HALF_UP).toPlainString();
    }
}
