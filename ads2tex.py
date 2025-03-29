#!/usr/bin/env python
from argparse import ArgumentParser

if __name__=="__main__":
    psr = ArgumentParser()
    psr.add_argument('infile')
    args = psr.parse_args()

    with open(args.infile, 'r') as f:
        lines = f.readlines() 

    lines2 = []
    nlines = len(lines)
    i = 0 
    while i < nlines:
        line = lines[i]
        print line
        line = line.replace("Petigura, E.~A.",r"{\bf Petigura, E.~A.}")
        line = line.replace("Petigura, E.",r"{\bf Petigura, E.}")
        line = line.replace(r"{\rsquo}",r"'")
        line = line.replace(r"{\rdquo}",r"'")
        line = line.replace(r"{\amp}",r"\&")
        line = line.replace(r"{&#10753;}",r"\oplus")
        line = line.replace(r"{\times}",r"$\times$")
        line = line.replace(r"{\ndash}",r"--")
        
        if line.count('Erratum')==1:
            while i < nlines:
                if lines[i].count('\item')==1:
                    break
                i+=1
            continue

        if line.count('Query Results')==1:
            i+=1
            continue
        if line.count('Total number selected')==1:
            i+=1
            continue

        lines2.append(line)
        i+=1

    lines = lines2 
    outfile = args.infile
    outfile = outfile.replace('ads','tex')

    with open(outfile,'w') as f:
        f.writelines(lines)

    print "created {}".format(outfile)
