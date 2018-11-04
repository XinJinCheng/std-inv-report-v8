#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'read_excel_util.py'

__author__ = 'kuoren'

import pandas as pd
import openpyxl as xl
import os

def read_excel(filePath):
    '''
    Read excel
    :param filePath:
    :return:
    '''
    print("loading file...")
    xls = pd.ExcelFile(filePath)
    df = xls.parse()
    return df

def writeExcel(dataFrame, filePath, sheetName):
    writer = pd.ExcelWriter(filePath)
    if os.path.exists(filePath) != True:
        dataFrame.to_excel(writer, sheetName, index=None)
    else:
        book = xl.load_workbook(writer.path)
        writer.book = book
        dataFrame.to_excel(excel_writer=writer, sheet_name = sheetName, index=None)
    writer.save()
    writer.close()

def writeExcelWithIndex(dataFrame, filePath, sheetName):
    writer = pd.ExcelWriter(filePath)
    if os.path.exists(filePath) != True:
        dataFrame.to_excel(writer, sheetName, index=True)
    else:
        book = xl.load_workbook(writer.path)
        writer.book = book
        dataFrame.to_excel(excel_writer=writer, sheet_name = sheetName, index=True)
    writer.save()
    writer.close()

if __name__ == "__main__":
    read_excel("../test-data/san-ming/cleaned/AnswerList1540806254513_cleaned_本科毕业生_public_analysis_20181102235123.xlsx")
