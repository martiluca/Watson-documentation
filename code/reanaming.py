#!/usr/bin/env python3

import csv
import os
import subprocess

def RenameFiles(FastqDir, RunId, FileName, DictRead, which):
    # First case: the RunId is in the dictionary -> this is not the first file for this id -> append the file and delete it
    if RunId in DictRead:
        try:
            OldPath = os.path.join(FastqDir, FileName)
            ToCat = os.path.join(FastqDir, f"FileToCat.temp.fastq.gz")
            os.rename(DictRead[RunId], ToCat)

            subprocess.run(f"cat {ToCat} {OldPath} > {DictRead[RunId]}", shell=True)

            os.remove(ToCat)
            os.remove(OldPath)

            print(f"Appended file {FileName} to {RunId}_{which}.fastq.gz")

        except FileNotFoundError as NotFound:
            print(f"File not found: {NotFound}")

    # Second case: the RunID is not in the dictionary -> this is the first file for this id -> rename it
    else:
        OldPath = os.path.join(FastqDir, FileName)
        NewPath = os.path.join(FastqDir, f"{RunId}_{which}.fastq.gz")
        try:
            os.rename(OldPath, NewPath)
            DictRead[RunId] = NewPath

            print(f"Renamed {which} file: {FileName} to {RunId}_{which}.fastq.gz")
        except FileNotFoundError as NotFound:
            print(f"File not found: {NotFound}")


