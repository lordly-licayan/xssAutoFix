import os, re, datetime, time, xlrd, xlsxwriter
from os.path import exists, join


def makeDirectory(folderPath):
    if not exists(folderPath):
        os.makedirs(folderPath)


def getFiles(path, fileNameList, fileExt='jsp'):
    filesDict = {}
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for file in f:
            filePath= join(r, file)
            index= re.search(fileExt, filePath)
            if index:
                srcFileName= filePath[index.start():]
                if srcFileName in fileNameList:
                    filesDict[srcFileName] = filePath

    return filesDict


def escapeChars(str):
    return str.replace('(','\(').replace(')','\)').replace('+','\+').replace('[','\[').replace(']','\]')


def makeReport(outputPath, unChangedFileList, filesWithIssues):
    workbook_name = join(outputPath, f'Automation_Result_{time.time_ns()}.xlsx')
    workbook = xlsxwriter.Workbook(workbook_name)
    header_1 = workbook.add_format({'bold': True})
    header_2 = workbook.add_format({'border' : 1,'bg_color' : '#C6EFCE'})
    border = workbook.add_format({'border': 1})

    #Create Sheet for unchanged Files.
    if unChangedFileList:
        fileSheet = workbook.add_worksheet('Unchanged files')
        fileSheet.set_column('A:A',8)
        fileSheet.set_column('B:B',50)

        fileSheet.write('B1','Filename:', header_1)
        fileSheetRow = 1
        fileSheetCol = 0

        for item in unChangedFileList:
            fileSheet.write_number(fileSheetRow, fileSheetCol, fileSheetRow)
            fileSheet.write_string(fileSheetRow, fileSheetCol+1, item, border)
            fileSheetRow +=1 

    # Create Sheet for Files with issues.
    fileSheet = workbook.add_worksheet('Files with issues')
    fileSheet.set_column('A:A',8)
    fileSheet.set_column('B:B',50)

    fileSheet.write('B1','Filename:', header_1)
    fileSheetRow = 1
    fileSheetCol = 0

    for item in filesWithIssues:
        fileSheet.write_number(fileSheetRow, fileSheetCol, fileSheetRow)
        fileSheet.write_string(fileSheetRow, fileSheetCol+1, item, border)
        fileSheetRow +=1 
    
    # Creating Sheet for detailed issues.
    findingsSheet = workbook.add_worksheet('QA')
    findingsSheet.set_column('B:B',40)
    findingsSheet.set_column('C:C',80)
    findingsSheet.set_column('D:D',10)
    findingsSheet.set_column('E:E',100)
    findingsSheet.set_column('F:F',150)
    findingsSheet.set_column('G:G',20)

    findingsSheet.write_string('B3', '脆弱性あるパラメータ', header_2)
    findingsSheet.write_string('C3', '該当資産', header_2)
    findingsSheet.write_string('D3', 'Line No.', header_2)
    findingsSheet.write_string('E3', '改修箇所', header_2)
    findingsSheet.write_string('F3', 'Actual content', header_2)
    findingsSheet.write_string('G3', 'Remarks', header_2)

    findingsSheetRow = 3
    findingsSheetCol = 1

    for issuesKey in filesWithIssues:
        itemList= filesWithIssues[issuesKey]
        for item in itemList:
            findingsSheet.write_string(findingsSheetRow, findingsSheetCol, item[0])
            findingsSheet.write_string(findingsSheetRow, findingsSheetCol+1, item[1])
            findingsSheet.write_string(findingsSheetRow, findingsSheetCol+2, item[2])
            findingsSheet.write_string(findingsSheetRow, findingsSheetCol+3, item[3])
            findingsSheet.write_string(findingsSheetRow, findingsSheetCol+4, item[4])
            findingsSheet.write_string(findingsSheetRow, findingsSheetCol+5, item[5])
            findingsSheetRow += 1

    workbook.close()