'''
Created on Apr 17, 2015

@author: ad
'''
import os, re, logging 
from django.template.loader import render_to_string
from lxml import etree 

logger = logging.getLogger(__name__)
currentDirectory = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIRECTORY = os.path.abspath(os.path.join(currentDirectory, os.pardir))

TEST_DATA_DIR_PATH = os.path.join(PROJECT_DIRECTORY, 
                                       'sequencelistings', 'testData')

SCREENSHOT_DIR = os.path.join(TEST_DATA_DIR_PATH, 'screenshots')
OUTPUT_DIR = os.path.join(PROJECT_DIRECTORY, 'sequencelistings',
                               'static', 'sequencelistings', 'output')

XML_SCHEMA_PATH = os.path.join(OUTPUT_DIR, 'resources', 'st26.xsd')

XML_DTD_PATH = os.path.join(OUTPUT_DIR, 'resources', 'ST26SequenceListing_V1_0.dtd')
# XML_DTD_PATH = os.path.join(OUTPUT_DIR, 'resources', 'cws_4_7-en-annex2-AN-II_amended.dtd')
MOLTYPE_DNA = 'DNA'
MOLTYPE_RNA = 'RNA'
MOLTYPE_AA = 'AA'

MOLTYPE_CHOICES = [('DNA', 'DNA'), ('RNA', 'RNA'), ('AA', 'AA')]

MOL_TYPE_QUALIFIER_VALUES = {'DNA': 'genomic DNA', 'RNA': 'genomic RNA', 'AA': 'protein'}

QUALIFIER_CHOICE = {'attenuator': [('allele', 'allele'),
                                    ('gene', 'gene'),
                                    ('gene_synonym', 'gene_synonym'),
                                    ('map', 'map'),
                                    ('note', 'note'),
                                    ('operon', 'operon'),
                                    ('phenotype', 'phenotype')],
                    'C_region': [('allele', 'allele'),
                                    ('gene', 'gene'),
                                    ('gene_synonym', 'gene_synonym'),
                                    ('map', 'map'),
                                    ('note', 'note'),
                                    ('product', 'product'),
                                    ('pseudo', 'pseudo'),
                                    ('pseudogene', 'pseudogene'),
                                    ('standard_name', 'standard_name')],
                    'CAAT_signal': [('allele', 'allele'),
                                    ('gene', 'gene'),
                                    ('gene_synonym', 'gene_synonym'),
                                    ('map', 'map'),
                                    ('note', 'note')],
                    }

# regex for formula
FORMULA_CHARS = '[a-zA-Z]+'
FORMULA_REGEX = r'(?P<head>%s)\((?P<region>%s)\)(?P<startOccurrence>\d+)(\.\.(?P<endOccurrence>\d+))?(?P<tail>%s)?' % (FORMULA_CHARS, FORMULA_CHARS, FORMULA_CHARS)
FORMULA_PATTERN = re.compile(FORMULA_REGEX)

def generate_list(inputFilePath):
    lis = []
    with open(inputFilePath, 'r') as f:
        for line in f:
            lis.append(line.strip())
    
    return lis 

fkdna = list(generate_list(os.path.join(PROJECT_DIRECTORY, 'sequencelistings', 'static', 'res', 'featureKey_dna.txt')))
fkprt = list(generate_list(os.path.join(PROJECT_DIRECTORY, 'sequencelistings', 'static', 'res', 'featureKey_prt.txt')))

FEATURE_KEYS_DNA = [(a, a) for a in fkdna] 
FEATURE_KEYS_PRT  = [(a, a) for a in fkprt] 

def rangeFromString(s):
    result = None # so no match
    rex = r'ra\((?P<startVal>\d+),(?P<stopVal>\d+),(?P<stepVal>\d+)\)'
    p = re.compile(rex)
    
    m = p.match(s)
    if m:
#         print 'match'
        try:
            startVal = int(m.group('startVal'))
            stopVal = int(m.group('stopVal'))
            stepVal = int(m.group('stepVal'))
            
#             print 'startVal', startVal
#             print 'stopVal', stopVal
#             print 'stepVal', stepVal
            
            result = range(startVal, stopVal, stepVal)
        except ValueError as ve:
            print '%s could not be converted to integer.' %s
            print ve
            
    return result

# TODO: cgt(ta)4.cg should not be accepted!
def expandFormula(aFormula):
    result = aFormula

    m = FORMULA_PATTERN.match(aFormula)
    if '(' in aFormula:
        if m:
            head = m.group('head')
            region = m.group('region')
            startOccurrence = m.group('startOccurrence')
            endOccurrence = m.group('endOccurrence')
            tail = m.group('tail')
            
            multip = int(startOccurrence)
            if endOccurrence:
                multip = int(endOccurrence)
            result = '%s%s' % (head, region*multip)
            if tail:
                result = '%s%s' % (result, tail)
        else:
            msg = 'The residues string contains "(" but does not match formula pattern. Residues: %s.' % aFormula
            logger.error(msg)
    return result 

def helper_generateXml(sl):
#     TODO: can eliminate sequences param as it can be obtained by the client from sl
    xml = render_to_string('xml_template.xml', {'sequenceListing': sl,
                            'sequences': sl.sequence_set.all(),
                            }).encode('utf-8', 'strict')

    outf = os.path.join(OUTPUT_DIR, '%s.xml' % sl.fileName)
    
    with open(outf, 'w') as gf:
        gf.write(xml) 
    
def validateDocumentWithSchema(aFilePath, aSchemaPath):
    result = False
    xmlschema_doc = etree.parse(aSchemaPath)
    xmlschema = etree.XMLSchema(xmlschema_doc)
    
    try:
        doc = etree.parse(aFilePath)
#         at this point the input file was successfully parsed
        
        if xmlschema.validate(doc):
            result = True
        else:
            logger.error('\n%s' % xmlschema.error_log)
    except etree.XMLSyntaxError as syntErr:
        logger.error('\n%s\n%s' % (aFilePath, syntErr))
    
    return result 

def validateDocumentWithDtd(afile, adtd):
    result = False
    with open(adtd, 'r') as d:
        dtd = etree.DTD(d)
        with open(afile, 'r') as f:
            try:
                fi = etree.XML(f.read())
                if dtd.validate(fi):
                    result = True
                else:
                    logger.error('\n%s\n%s' % (afile, 
                                             dtd.error_log.filter_from_errors()[0]))
            except etree.XMLSyntaxError as e:
                logger.error('\n%s\n%s' % (afile, e)) 
    return result

# helper used to generate XML code for the schema 

def generateXmlSchemaFeatureKeyValuesEnumeration():
    for fk in fkdna + fkprt:
        print '<xs:enumeration value="%s"/>' % fk 

# generateXmlSchemaFeatureKeyValuesEnumeration()

