VALUE_EQUAL_SEARCH_PATTERN_1= r'{}\s*=\s*"<%=(.*?)%>"'
VALUE_EQUAL_SEARCH_PATTERN_1_1= r'{}=<%=(.*?)%>'
VALUE_EQUAL_SEARCH_PATTERN_2= r'<%=(.*?)%>'
VALUE_EQUAL_SEARCH_PATTERN_3= r'\+\s*(\w+?|\w+\(\w*\)\B|\w+\[\w\]|\w+?|\w+[.]\w+)\s*[\+;]'
VALUE_EQUAL_SEARCH_PATTERN_4= r'\$\(\"(\w*)\"\)\.value'

VALUE_EQUAL_SUB_PATTERN= r'<%=(\s*){}(\s*)%>'
VALUE_EQUAL_SUB_PATTERN_3_1= r'\+\s*{}\s*\+'
VALUE_EQUAL_SUB_PATTERN_3_2= r'\+\s*{}\s*;'
VALUE_EQUAL_SUB_PATTERN_4= r'\$\(\"{}\"\)\.value'

VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_1= r'<%= {}({}) %>'
VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_3_1= r'+ {}({}) +'
VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_3_2= r'+ {}({});'
VALUE_EQUAL_SUB_PATTERN_REPLACEMENT_4= r'{}($("{}").value)'

ESCAPE_UTIL= 'org.apache.commons.text.StringEscapeUtils.escapeHtml4'
ESCAPE= 'escape'
JSP_TAG= '<%='
FIXED_PATTERN= r'{}\({}\)'

PARAMETER_VALUE= 0
LINE_NO= 2
LINE_CONTENT= 3

FIX_SKIP= 0
FIX_SUCCESSFUL= 1
FIX_MISMATCH= 2
FIX_NOT_MODIFIED= 3
FIX_FINDINGS_EXCEED= 4
FIX_ALREADY_DONE= 5

FIX_RESULT={
    FIX_SUCCESSFUL: 'SUCCESS',
    FIX_MISMATCH: 'Mismatch Line Content.',
    FIX_NOT_MODIFIED: 'Line has not been modified.',
    FIX_FINDINGS_EXCEED: 'Number of values=<%=%> is more than 1.',
    FIX_ALREADY_DONE: 'Fix already done'
}
