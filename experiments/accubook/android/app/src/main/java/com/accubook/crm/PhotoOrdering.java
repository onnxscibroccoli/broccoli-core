package com.accubook.crm;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Safe stable-filename photo ordering; no path operations or Android dependencies. */
public final class PhotoOrdering {
    private PhotoOrdering(){}
    public static boolean valid(String name){
        return name!=null&&name.matches(
            "PHOTO-[a-f0-9]{32}\\.(jpg|png|webp|heic|heif|avif|gif|bmp|tiff|dng|img)");
    }
    public static List<String> merge(List<String> present,List<String> stored)
        throws IOException {
        if(present==null||stored==null||present.size()>2000||stored.size()>2000)
            throw new IOException("Invalid photo index size");
        Set<String> all=new HashSet<>();
        for(String file:present)
            if(!valid(file)||!all.add(file))throw new IOException("Invalid photo file list");
        List<String> merged=new ArrayList<>();
        Set<String> seen=new HashSet<>();
        for(String file:stored){
            if(!valid(file)||!seen.add(file)||!all.contains(file))
                throw new IOException("Photo order contains a missing or duplicated photo");
            merged.add(file);
        }
        List<String> tail=new ArrayList<>();
        for(String file:present)if(!seen.contains(file))tail.add(file);
        Collections.sort(tail);
        merged.addAll(tail);
        return merged;
    }
    public static List<String> move(List<String> ordered,String file,int destination)
        throws IOException {
        if(ordered==null||ordered.size()>2000)
            throw new IOException("Invalid photo order");
        List<String> changed=merge(ordered,ordered);
        int from=changed.indexOf(file);
        if(from<0||destination<0||destination>=changed.size())
            throw new IOException("Photo destination invalid");
        changed.add(destination,changed.remove(from));
        return changed;
    }
}
