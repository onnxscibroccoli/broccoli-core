package com.accubook.crm;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.Arrays;

/** JVM-only tests: encryption, authentication, wrong password and tampering. */
public final class SecureArchiveSmoke {
    private static void require(boolean ok,String message) {
        if(!ok)throw new AssertionError(message);
    }
    public static void main(String[] unused) throws Exception{
        File dir=Files.createTempDirectory("accubook-crypto-").toFile();
        byte[] data="Accubook local private export test — estimate records\n"
            .getBytes(java.nio.charset.StandardCharsets.UTF_8);
        char[] pass="long unique passphrase for offline export".toCharArray();
        ByteArrayOutputStream encrypted=new ByteArrayOutputStream();
        try(java.io.OutputStream out=SecureArchive.encryptStream(encrypted,pass)){
            out.write(data);
        }
        byte[] ciphertext=encrypted.toByteArray();
        require(ciphertext.length>data.length+20,"Encrypted header/tag absent");
        require(!new String(ciphertext,java.nio.charset.StandardCharsets.ISO_8859_1)
            .contains("estimate records"),"Cleartext leaked into ciphertext");
        File restored=SecureArchive.decryptToTemp(
            new ByteArrayInputStream(ciphertext),dir,pass);
        require(Arrays.equals(data,Files.readAllBytes(restored.toPath())),"Round trip failed");
        require(restored.delete(),"Cannot delete test plaintext");

        boolean wrong=false;
        try{
            SecureArchive.decryptToTemp(new ByteArrayInputStream(ciphertext),dir,
                "incorrect secure passphrase".toCharArray());
        }catch(IOException expected){wrong=true;}
        require(wrong,"Wrong passphrase accepted");

        byte[] altered=ciphertext.clone();
        altered[altered.length-2]^=(byte)0x40;
        boolean tamper=false;
        try{SecureArchive.decryptToTemp(new ByteArrayInputStream(altered),dir,pass);}
        catch(IOException expected){tamper=true;}
        require(tamper,"Tampered ciphertext accepted");
        File[] remaining=dir.listFiles();
        require(remaining!=null&&remaining.length==0,
            "Authentication failure left private plaintext temporary files");
        Arrays.fill(pass,'\0');
        require(dir.delete(),"Test directory cleanup failed");
        System.out.println("SecureArchiveSmoke: PASS (AES-GCM, tamper/wrong key, no temp leak)");
    }
}
