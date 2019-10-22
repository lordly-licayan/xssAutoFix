import configparser, os, re, datetime, time
import logging
from pathlib import Path
from os.path import exists, join
from shutil import copyfile
from helper import *
from constants import *

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

currentPath= Path(__file__).resolve().parent
config_file = join(currentPath, 'config.ini')
config = configparser.ConfigParser()
config.read(config_file, encoding='UTF-8')
indicator = config['SHEET']['FINDINGS_INDICATOR']


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


def getLineContentDict(findingsInfoList):
    lineContentDict = {}
    lineNoDict= {}
    for item in findingsInfoList:
        itemKey= item[LINE_CONTENT].lower().strip()
        itemList= []
        lineNoList= []

        if itemKey in lineContentDict:
            itemList= lineContentDict[itemKey]
            lineNoList= lineNoDict[itemKey]

        itemList.append(item)
        lineNoList.append(item[LINE_NO])

        lineContentDict[itemKey]= itemList
        lineNoDict[itemKey]= lineNoList
    return lineContentDict, lineNoDict


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


def doFix(line, parameterValue):    
    fixed= line
    resultList= re.findall(VALUE_EQUAL_SEARCH_PATTERN_1.format('value'), line, re.IGNORECASE)        
    if len(resultList) == 0:
        resultList= re.findall(VALUE_EQUAL_SEARCH_PATTERN_1_1.format(parameterValue), line, re.IGNORECASE)
        
    if len(resultList) == 1:
        valueName= resultList[0].strip()
        if ESCAPE_UTIL in valueName:
            return FIX_SKIP, None

        fixed= re.sub(VALUE_EQUAL_SUB_PATTERN.format(parameterValue), VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_1.format(ESCAPE_UTIL, valueName), line, re.IGNORECASE)
        if line == fixed:
            fixed= re.sub(VALUE_EQUAL_SUB_PATTERN.format(escapeChars(valueName)), VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_1.format(ESCAPE_UTIL, valueName), line, re.IGNORECASE)
    elif len(resultList) > 1:
        return FIX_FINDINGS_EXCEED, None
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

    if line == fixed and any(fixedIndicator not in line for fixedIndicator in [ESCAPE_UTIL, ESCAPE]):
        return FIX_NOT_MODIFIED, None
    else:
        return FIX_SUCCESSFUL, fixed

        
def process(findingsInfoDict, sourceFileDict, destinationPath, resultDict, encoding):
    
    filesWithIssues= {}
    unChangedFileList= []

    for fileNameKey in sourceFileDict:
        sourceFileName= sourceFileDict[fileNameKey]
        findingsInfoList= findingsInfoDict[fileNameKey]
        lineNoDict= getLineNoDict(findingsInfoList)
        lineContentDict, lineNoContentDict= getLineContentDict(findingsInfoList)
        misMatchedDict= {}
        fixedMisMatchedList= []
        hasBeenFixed= False
        
        lastIndex= fileNameKey.rfind('\\')
        parentPath= fileNameKey[:lastIndex]
        fileName= fileNameKey[lastIndex+1:]
        programName= fileNameKey[lastIndex+1:fileNameKey.rfind('.')]
        beforePath = '{}\\{}\\Before\\{}'.format(destinationPath, programName, parentPath)
        afterPath = '{}\\{}\\After\\{}'.format(destinationPath, programName, parentPath)
        
        makeDirectory(beforePath)
        makeDirectory(afterPath)

        copyfile(sourceFileName, '{}\\{}'.format(beforePath, fileName))
        after = open('{}\\{}'.format(afterPath, fileName), 'w', encoding= encoding)

        with open(sourceFileName, 'rt', encoding= encoding) as fp:
            print("sourceFileName: %s" %sourceFileName)
            lineNo= 0
            
            for line in fp:
                lineNo+= 1
                lineNoKey= str(lineNo)
                keyName= line.lower().strip()
                result= FIX_SKIP

                if 'HyoukiJoukenLstcondition.jsp' in sourceFileName and lineNo == 402:
                    me= True

                if keyName in lineContentDict:
                    lineContentList= lineContentDict[keyName]
                    lineNoContentList= lineNoContentDict[keyName]
                    
                    if lineNo not in lineNoContentList:
                        for lineContent in lineContentList:
                            parameterValue= lineContent[0]
                            result, fixed= doFix(line, parameterValue)
                            if result == FIX_SUCCESSFUL:
                                line= fixed
                                hasBeenFixed= True
                                fixedMisMatchedList.append(keyName)
                                if keyName in misMatchedDict:
                                    issueList= misMatchedDict[keyName]
                                    if issueList:
                                        del issueList[0]
                                break

                if lineNoKey in lineNoDict:
                    lineNoFindingList= lineNoDict[lineNoKey]

                    for lineNoFinding in lineNoFindingList:
                        lineInFindings= lineNoFinding[3]
                        keyName= lineNoFinding[3].lower().strip()

                        if keyName in fixedMisMatchedList:
                            fixedMisMatchedList.remove(keyName)
                        else:
                            if (re.sub('\s', '', line.strip().lower()) == re.sub('\s', '', lineInFindings.strip().lower())):
                                parameterValue= lineNoFinding[0].strip()
                                result, fixed= doFix(line, parameterValue)
                                if result != FIX_SUCCESSFUL:
                                    logFileWithIssues(filesWithIssues, fileName, [lineNoFinding[0], lineNoFinding[1], str(lineNo), lineNoFinding[3], line, FIX_RESULT[result]])                       
                                else:
                                    line= fixed
                                    hasBeenFixed= True
                            elif any(fixedIndicator in line for fixedIndicator in [ESCAPE_UTIL, ESCAPE]):
                                continue
                            else:
                                issueList= []
                                if keyName in misMatchedDict:
                                    issueList= misMatchedDict[keyName]
                                issueList.append([fileName, lineNoFinding[0], lineNoFinding[1], str(lineNo), lineNoFinding[3], line, FIX_RESULT[FIX_MISMATCH]])
                                misMatchedDict[keyName]= issueList
                            
                after.write(line)
        if not after.closed:
            after.close()

        if not hasBeenFixed:
            unChangedFileList.append(fileName)

        for keyName in fixedMisMatchedList:
            if keyName in misMatchedDict:
                issueList= misMatchedDict[keyName]
                for item in issueList:
                    item[6]= FIX_RESULT[FIX_ALREADY_DONE]

        for misMatchedKey in misMatchedDict:
            issueList= misMatchedDict[misMatchedKey]
            for item in issueList:
                fileNameKey= item[0]
                del item[0]
                logFileWithIssues(filesWithIssues, fileName, item)

    makeReport(destinationPath, unChangedFileList, filesWithIssues)

if __name__ == "__main__":
    try:
        start = datetime.datetime.now()
        print(f'\nInitializing...\nTime started: {start}')
        
        findingsInfoDict= getFindingsInfo()
        sourcePath= config['PATH']['SOURCE_CODE_PATH']
        sourceFileDict= getFiles(sourcePath, findingsInfoDict.keys())

        outputFolder= config['PATH']['OUTPUT_FOLDER']
        outputPath= config['PATH']['OUTPUT_PATH']

        if outputPath:
            destinationPath= join(outputPath, outputFolder)
        else:
            destinationPath= join(currentPath, outputFolder)
        #time to read all the files involve
        resultDict= {}
        encoding= config['OTHERS']['ENCODING']
        process(findingsInfoDict, sourceFileDict, destinationPath, resultDict, encoding)
        
        finish = datetime.datetime.now()
        print(f'\nTime elapsed:\n{finish - start}')
        
    except Exception as err:
        logger.error(str(err), exc_info=True)
        input('')
