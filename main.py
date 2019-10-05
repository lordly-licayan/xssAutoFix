import configparser, os, re, datetime, time, xlrd, xlsxwriter
from pathlib import Path
from os.path import exists
from shutil import copyfile


config_file = os.path.join(Path(__file__).resolve().parent, 'config.ini')
config = configparser.ConfigParser()
config.read(config_file,encoding='UTF-8')

VALUE_EQUAL_SEARCH_PATTERN_1= r'{}="<%=(.*?)%>"'
VALUE_EQUAL_SEARCH_PATTERN_1_1= r'{}=<%=(.*?)%>'
VALUE_EQUAL_SEARCH_PATTERN_2= r'<%=(.*?)%>'
VALUE_EQUAL_SEARCH_PATTERN_3= r'\+\s*(\w+?|\w+\(\w*\)\B|\w+\[\w\]|\w+?|\w+[.]\w+)\s*[\+;]'
VALUE_EQUAL_SEARCH_PATTERN_4= r'\$\(\"(\w*)\"\)\.value'
VALUE_EQUAL_SEARCH_PATTERN_5= r'{}.value'

VALUE_EQUAL_SUB_PATTERN= r'<%=(\s*){}(\s*)%>'
VALUE_EQUAL_SUB_PATTERN_3_1= r'\+\s*{}\s*\+'
VALUE_EQUAL_SUB_PATTERN_3_2= r'\+\s*{}\s*;'
VALUE_EQUAL_SUB_PATTERN_4= r'\$\(\"{}\"\)\.value'
VALUE_EQUAL_SUB_PATTERN_5= r'{}'

VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_1= r'<%= {}({}) %>'
VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_3_1= r'+ {}({}) +'
VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_3_2= r'+ {}({});'
VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_4= r'{}($("{}").value)'
VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_5= r' {}({}) '

ESCAPE_UTIL = config['OTHERS']['ESCAPE_UTIL']
ESCAPE= 'escape'
JSP_TAG= '<%='
FIXED_PATTERN= r'{}\({}\)'
LINE_NO= 2

AUTOMATION_FINDING_1= "Mismatch Line Content."
AUTOMATION_FINDING_2= "Line has not been modified."
AUTOMATION_FINDING_3= "Number of values=<%=%> is more than 1."

outputFolder= config['PATH']['OUTPUT_FOLDER'] 
indicator = config['SHEET']['FINDINGS_INDICATOR']


def makeDirectory(folderPath):
    if not exists(folderPath):
        os.makedirs(folderPath)


def getFindingsInfo():
    findingsFileName= config['FILE']['FINDINGS_FILE_NAME']
    sheetName = config['SHEET']['SHEET_NAME']
    rowIndicator= int(config['SHEET']['ROW_INDICATOR'])
    rowParameterValue= int(config['SHEET']['ROW_PARAMETER_VALUE'])
    rowFileName= int(config['SHEET']['ROW_FILE_NAME'])
    rowLineNo= int(config['SHEET']['ROW_LINE_NO'])
    rowLineContent= int(config['SHEET']['ROW_LINE_CONTENT'])    
    filesToFind = config['OTHERS']['FILES_TO_FIND']

    infoDict = {}
    xlsx = xlrd.open_workbook(findingsFileName)
    sheet = xlsx.sheet_by_name(sheetName)

    for row in sheet._cell_values:
        if row[rowIndicator] == indicator and any(row[rowFileName].endswith(f'{extension}') for extension in filesToFind):
            fileName= row[rowFileName][re.search(filesToFind, row[rowFileName]).start():]
            lineNoIndex= re.search(r'\((\w*)', row[rowLineNo])
            lineNo= int(row[rowLineNo][lineNoIndex.start()+1:lineNoIndex.end()])
            
            itemList=[]
            itemList.append(row[rowParameterValue])
            itemList.append(fileName)
            itemList.append(lineNo)
            itemList.append(row[rowLineContent])

            info= infoDict.get(fileName)
            if info is None:
                info=[]
            
            info.append(itemList)
            infoDict[fileName]= info
    
    #make sure to sort into ascending the Line no.
    for item in infoDict:
        infoDict[item].sort(key=lambda byItem: byItem[LINE_NO])        
        
    return infoDict


def logFileWithIssues(filesWithIssues, keyName, lineNoIssueList):
    issuesList= []
    if keyName in filesWithIssues:
        issuesList= filesWithIssues[keyName]
    issuesList.append(lineNoIssueList)
    filesWithIssues[keyName]= issuesList
                 

def getFiles(path, fileNameList, fileExt='jsp'):
    filesDict = {}
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for file in f:
            filePath= os.path.join(r, file)
            index= re.search(fileExt, filePath)
            if index:
                srcFileName= filePath[index.start():]
                if srcFileName in fileNameList:
                    filesDict[srcFileName] = filePath

    return filesDict


def escapeChars(str):
    return str.replace('(','\(').replace(')','\)').replace('+','\+').replace('[','\[').replace(']','\]')


def getLineNoDict(findingsInfoList):
    lineNoDict = {}
    for item in findingsInfoList:
        lineNoKey= str(item[LINE_NO])
        lineNoList= []
        if lineNoKey in lineNoDict:
            lineNoList= lineNoDict[lineNoKey]
        lineNoList.append(item)
        lineNoDict[lineNoKey]= lineNoList
    return lineNoDict


def hasFixed(line, subPatternList, escapingValue, parameterValue):
    for pattern in subPatternList:
        existList= re.findall(FIXED_PATTERN.format(escapingValue, pattern.format(parameterValue)), line, re.IGNORECASE)
        if existList:
            return True


def getFix(line, searchPattern, subPatternList, replacementPatternList, escapingValue, parameterValue):
    fixed= line
    
    if hasFixed(line, subPatternList, escapingValue, parameterValue):
        return fixed

    resultList= re.findall(searchPattern.format(parameterValue), line, re.IGNORECASE)

    if len(resultList) > 0:
        valueNameList = [result.strip() for result in resultList]
        for item in valueNameList:
            if escapingValue in item:
                continue
            item= item.strip()
            if parameterValue.lower() in item.lower() or item.lower() in parameterValue.lower() or (JSP_TAG not in line and parameterValue in line):
                for i in range(len(subPatternList)):
                    fixed= re.sub(subPatternList[i].format(escapeChars(item)), replacementPatternList[i].format(escapingValue, item), line, re.IGNORECASE)
                    if line == fixed:
                        fixed= re.sub(subPatternList[i].format(parameterValue), replacementPatternList[i].format(escapingValue, item), line, re.IGNORECASE)
    return fixed


def makeReport(outputPath, filesWithIssues):
    workbook_name = os.path.join(outputPath, f'Automation_Result_{time.time_ns()}.xlsx')
    workbook = xlsxwriter.Workbook(workbook_name)
    header_1 = workbook.add_format({'bold': True})
    header_2 = workbook.add_format({'border' : 1,'bg_color' : '#C6EFCE'})
    border = workbook.add_format({'border': 1})

    # Creating first sheet
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
    
    # Creating second sheet
    findingsSheet = workbook.add_worksheet('QA')
    findingsSheet.set_column('B:B',40)
    findingsSheet.set_column('C:C',80)
    findingsSheet.set_column('D:D',10)
    findingsSheet.set_column('E:E',100)
    findingsSheet.set_column('F:F',150)
    findingsSheet.set_column('G:G',20)

    findingsSheet.write_string('B3', 'Parameter variable', header_2)
    findingsSheet.write_string('C3', 'FileName', header_2)
    findingsSheet.write_string('D3', 'Line No.', header_2)
    findingsSheet.write_string('E3', 'Findings content', header_2)
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

def process(findingsInfoDict, sourceFileDict, resultDict, encoding):
    outputPath= os.path.join(Path(__file__).resolve().parent, outputFolder)
    filesWithIssues= {}

    for fileNameKey in sourceFileDict:
        sourceFileName= sourceFileDict[fileNameKey]
        findingsInfoList= findingsInfoDict[fileNameKey]
        lineNoDict= getLineNoDict(findingsInfoList)
        
        lastIndex= fileNameKey.rfind('\\')
        parentPath= fileNameKey[:lastIndex]
        fileName= fileNameKey[lastIndex+1:]
        programName= fileNameKey[lastIndex+1:fileNameKey.rfind('.')]
        beforePath = os.path.join(outputFolder, '{}\\{}\\Before\\{}'.format(outputPath, programName, parentPath))
        afterPath = os.path.join(outputFolder, '{}\\{}\\After\\{}'.format(outputPath, programName, parentPath))
        
        makeDirectory(beforePath)
        makeDirectory(afterPath)

        copyfile(sourceFileName, '{}\\{}'.format(beforePath, fileName))
        after = open('{}\\{}'.format(afterPath, fileName), 'w', encoding='UTF-8')

        with open(sourceFileName, 'rt', encoding=encoding) as fp:
            print("sourceFileName: %s" %sourceFileName)
            lineNo= 0

            for line in fp:
                lineNo+= 1
                lineNoKey= str(lineNo)
                if lineNoKey in lineNoDict:
                    lineNoFindingList= lineNoDict[lineNoKey]
                    originalLine= line
                    
                    for lineNoFinding in lineNoFindingList:
                        if (re.sub('\s', '', originalLine.strip().lower()) == re.sub('\s', '', lineNoFinding[3].strip().lower())):
                            fixed= line
                            #print("Line no: {}-> {};{}".format(lineNo, findingsInfo[0], line))

                            parameterValue= lineNoFinding[0].strip()
                            resultList= re.findall(VALUE_EQUAL_SEARCH_PATTERN_1.format('value'), line, re.IGNORECASE)
                            
                            if len(resultList) == 0:
                                resultList= re.findall(VALUE_EQUAL_SEARCH_PATTERN_1_1.format(parameterValue), line, re.IGNORECASE)
                                
                            if len(resultList) == 1:
                                valueName= resultList[0].strip()
                                if ESCAPE_UTIL in valueName:
                                    continue
                                fixed= re.sub(VALUE_EQUAL_SUB_PATTERN.format(parameterValue), VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_1.format(ESCAPE_UTIL, valueName), line, re.IGNORECASE)
                                if line == fixed:
                                    fixed= re.sub(VALUE_EQUAL_SUB_PATTERN.format(escapeChars(valueName)), VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_1.format(ESCAPE_UTIL, valueName), line, re.IGNORECASE)
                            elif len(resultList) > 1:
                                logFileWithIssues(filesWithIssues, sourceFileName, [lineNoFinding[0], sourceFileName, str(lineNo), lineNoFinding[3], line, AUTOMATION_FINDING_3])
                                #print("->WARNING: line not fixed. -> {} -> {} -> {} -> {}".format(fileName, lineNo, lineNoFinding[0], line))
                            else:
                                subPatternList= [VALUE_EQUAL_SUB_PATTERN]
                                replacementList= [VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_1]
                                fixed= getFix(line, VALUE_EQUAL_SEARCH_PATTERN_2, subPatternList, replacementList, ESCAPE_UTIL, parameterValue)
                                                                    
                                if line == fixed:
                                    subPatternList= [VALUE_EQUAL_SUB_PATTERN_3_1, VALUE_EQUAL_SUB_PATTERN_3_2]
                                    replacementList= [VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_3_1, VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_3_2]
                                    fixed= getFix(line, VALUE_EQUAL_SEARCH_PATTERN_3, subPatternList, replacementList, ESCAPE, parameterValue)
                                    
                                if line == fixed:
                                    subPatternList= [VALUE_EQUAL_SUB_PATTERN_4]
                                    replacementList= [VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_4]
                                    fixed= getFix(line, VALUE_EQUAL_SEARCH_PATTERN_4, subPatternList, replacementList, ESCAPE, parameterValue)

                                if line == fixed:
                                    subPatternList= [VALUE_EQUAL_SUB_PATTERN_5]
                                    replacementList= [VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_5]
                                    fixed= getFix(line, VALUE_EQUAL_SEARCH_PATTERN_5, subPatternList, replacementList, ESCAPE, parameterValue)

                            if line == fixed and (ESCAPE_UTIL not in line or ESCAPE not in line):
                                logFileWithIssues(filesWithIssues, sourceFileName, [lineNoFinding[0], sourceFileName, str(lineNo), lineNoFinding[3], line, AUTOMATION_FINDING_2])
                                #print("->WARNING: line not fixed. -> {} -> {} -> {} -> {}".format(fileName, lineNo, lineNoFinding[0], line))
                            else:         
                                line= fixed
                        else:
                            logFileWithIssues(filesWithIssues, sourceFileName, [lineNoFinding[0], sourceFileName, str(lineNo), lineNoFinding[3], line, AUTOMATION_FINDING_1])
                            #print("->ISSUE: Mismatch line findings. ->{} ->{} -> {} -> {} -> {}".format(fileName, lineNo, lineNoFinding[0], lineNoFinding[3], line))
                after.write(line)

        if not after.closed:
            after.close()
    
    makeReport(outputPath, filesWithIssues)

if __name__ == "__main__":
    try:
        start = datetime.datetime.now()
        findingsInfoDict= getFindingsInfo()
        sourcePath= config['PATH']['SOURCE_CODE_PATH']
        sourceFileDict= getFiles(sourcePath, findingsInfoDict.keys())

        #time to read all the files involve
        resultDict= {}
        encoding= config['OTHERS']['ENCODING']
        process(findingsInfoDict, sourceFileDict, resultDict, encoding)
        
        finish = datetime.datetime.now()
        print(f'\nTime elapsed:\n{finish - start}')
        
    except Exception as err:
        print(f'Error found!\n{err}\n')
