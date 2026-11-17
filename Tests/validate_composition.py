#!/usr/bin/env python3
"""Read-only source/target/method checks. Never invokes Xcode or a simulator."""
from pathlib import Path
import hashlib,json,re,copy,plistlib,struct,xml.etree.ElementTree as ET
from openstep_reader import parse
ROOT=Path(__file__).resolve().parents[1]
APP='HalalAnalyzer حلال ام حرام؟'
QA=ROOT/'Tests/NativeQA'
EVIDENCE=ROOT/'Tests/Evidence'
EXPECTED_PRODUCT={
 'ContentView.swift':'06b6d75101b40eb4b99b9b59c1de876e54b6df85f772b3ed633f7fcf1a83a2fc',
 'IngredientScreening.swift':'fc8aab56d0fbdf7682cc77bf74a0a1811c813e93447b6985379f24c122e4167a',
 'ScreeningLocalization.swift':'097a18920ff95fda968c6cee1591360b50b0c077673bf40cb6c0970e8aa8be70',
 'PrivacyInfo.xcprivacy':'a331d51864743ebe4e00dd22360b4a538b6b3ac26a6b3eb54094e60a36959a12'}
QAID='com.saleh.halaltag.productioncomposition.qa.r20261117r7'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def method_bodies(text):
    # These fixed fixtures have no multiline Swift strings. Ignore quoted strings
    # and comments while finding method-closing braces; retain original bytes.
    result={}
    for match in re.finditer(r'^    func (test\w+)\([^\n]*\{',text,re.M):
        i=match.end();start=i;depth=1;quoted=False;escaped=False
        while depth:
            assert i<len(text),'unterminated method'
            c=text[i]
            if quoted:
                if escaped:escaped=False
                elif c=='\\':escaped=True
                elif c=='"':quoted=False
                i+=1;continue
            if text.startswith('//',i):
                end=text.find('\n',i);i=len(text) if end<0 else end+1;continue
            if text.startswith('/*',i):
                end=text.find('*/',i+2);assert end>=0;i=end+2;continue
            if c=='"':quoted=True
            elif c=='{':depth+=1
            elif c=='}':depth-=1
            i+=1
        assert match.group(1) not in result,'duplicate method'
        result[match.group(1)]=text[match.start():i]
    return result

def function_bodies(text):
    # These fixed fixtures have no multiline Swift strings. Ignore quoted strings
    # and comments while finding method-closing braces; retain original bytes.
    result={}
    for match in re.finditer(r'^    (?:private |override )?func (\w+)\([^\{]*\{',text,re.M):
        i=match.end();start=i;depth=1;quoted=False;escaped=False
        while depth:
            assert i<len(text),'unterminated method'
            c=text[i]
            if quoted:
                if escaped:escaped=False
                elif c=='\\':escaped=True
                elif c=='"':quoted=False
                i+=1;continue
            if text.startswith('//',i):
                end=text.find('\n',i);i=len(text) if end<0 else end+1;continue
            if text.startswith('/*',i):
                end=text.find('*/',i+2);assert end>=0;i=end+2;continue
            if c=='"':quoted=True
            elif c=='{':depth+=1
            elif c=='}':depth-=1
            i+=1
        assert match.group(1) not in result,'duplicate method'
        result[match.group(1)]=text[match.start():i]
    return result


def main():
    checks=[]
    def check(ok,label):
        if not ok:raise AssertionError(label)
        checks.append(label)
    original=(EVIDENCE/'OriginalTen-HalalTagPreparedUITests.swift.txt').read_text()
    functional=(QA/'UITests/HalalTagFunctionalUITests.swift').read_text()
    old_methods=method_bodies(original);new_methods=method_bodies(functional)
    check(len(old_methods)==len(new_methods)==10 and old_methods==new_methods,
          'all ten original functional method bodies byte-identical and in original order')
    check(list(old_methods)==list(new_methods),'original ten source order retained')
    for helper in ['assertInformationSheet','closeInformationSheet','tapVisible','tapLowerContentControl',
                   'isFullyVisible','requireFullyVisible','requirePresent','requireEventually','fail','capture','attachText']:
        pattern=r'    (?:private )?func '+helper+r'\b'
        # Compare the unchanged suffix from assertInformationSheet to the class end.
        check(re.search(pattern,functional) is not None,'original helper retained '+helper)
    old_suffix=original[original.index('    private func assertInformationSheet()'):original.index('\nprivate enum PreparationFailure:')]
    new_suffix=functional[functional.index('    private func assertInformationSheet()'):].rstrip()+'\n'
    check(old_suffix.rstrip()==new_suffix.rstrip(),'all original interaction, visibility, timeout, gesture and capture helpers byte-identical')
    old_mid=original[original.index('    // MARK: Existing accessibility labels'):original.index('    private func assertCombinedMatch(')]
    new_mid=functional[functional.index('    // MARK: Existing accessibility labels'):functional.index('    private func assertCombinedMatch(')]
    check(old_mid==new_mid,'all original editor, outcome, state and exact-copy helpers byte-identical')
    check('matches.count == 1' in functional and 'children.count == 4' in functional and
          'card.elementType != .staticText' in functional and 'children.prefix(3).map(\\.label)' in functional and
          'children[3].label.contains(fragments[3])' in functional and
          'containerFrame.insetBy(dx: -2, dy: -2).contains(frame)' in functional and
          'frame.minY >= previousBottom - 2' in functional,
          'adapted match helper requires unique real card, four ordered visible-text rectangles and all original fragments')
    check(functional.count('app.launch()')==1 and '"--language-launch-id", UUID().uuidString' in functional and
          '"--appearance-case", "light-large"' in functional and '-AppleLanguages' in functional,
          'functional setup binds one fresh light-large English QA process with unique receipt path')
    check('private struct QAInstallation' not in functional and 'QAInstallation.loadConfiguration' in functional,
          'functional fixture uses the shared stronger four-source-hash isolation guard')
    nine_names=['HalalTagPreparedUITests.swift','HalalTagArabicAppearanceUITests.swift','HalalTagLanguageStateUITests.swift']
    nine_total=0
    def without_comments(s):return re.sub(r'(?m)^\s*///.*\n','',s)
    for name in nine_names:
        old=(EVIDENCE/'ReviewedNine'/(name+'.txt')).read_text();new=(QA/'UITests'/name).read_text()
        if name == 'HalalTagPreparedUITests.swift':
            previous_content_pin = "0e325df994491b1d1daf60eb69d4bf5d2186867717ba71c901dc4e18fb325099"
            check(old.count(previous_content_pin) == 1 and new.count(EXPECTED_PRODUCT['ContentView.swift']) == 1,
                  'only the explicit reviewed R6 source binding changes in the original shared QA guard')
            old = old.replace(previous_content_pin, EXPECTED_PRODUCT['ContentView.swift'])
            previous_localization_pin = "7311a8c17857ed07161bac107911670c0edfdec5b8169fb8e08cb85739a92e4e"
            check(old.count(previous_localization_pin) == 1 and new.count(EXPECTED_PRODUCT['ScreeningLocalization.swift']) == 1,
                  'only the exact reviewed R6 localization hash changes in the shared QA guard')
            old = old.replace(previous_localization_pin, EXPECTED_PRODUCT['ScreeningLocalization.swift'])
            previous_model_pin = "bf98d94670058cb2a810ae9bb3866053bd9b706eee6d8503b9f459caa683bfe2"
            check(old.count(previous_model_pin) == 1 and new.count(EXPECTED_PRODUCT['IngredientScreening.swift']) == 1,
                  'only the exact reviewed R6 model hash changes in the shared QA guard')
            old = old.replace(previous_model_pin, EXPECTED_PRODUCT['IngredientScreening.swift'])
        check(method_bodies(old)==method_bodies(new), 'all original top-level native method bodies byte-identical '+name)
        if name == 'HalalTagLanguageStateUITests.swift':
            check(without_comments(old)==without_comments(new), 'language state fixture bytes unchanged '+name)
        else:
            previous_functions, current_functions = function_bodies(old), function_bodies(new)
            changed_helpers = {'journey','readPorkEvidence','reveal','readBlock','drag','capture'}
            added_helpers = {'beginBudget','finishBudget','revealTogether','auditPreservingViewport',
                             'privacyLinks','preparePrivacySection','auditPrivacyLinks'}
            check(set(current_functions)==set(previous_functions)|added_helpers,
                  'only reviewed measured-geometry helpers added '+name)
            check(all(body==current_functions[key] for key,body in previous_functions.items() if key not in changed_helpers),
                  'all unrelated interaction, timeout, viewport, audit and failure helpers remain byte-identical '+name)
            if name == 'HalalTagPreparedUITests.swift':
                check(old[old.index('enum PreparationFailure:'):]==new[new.index('enum PreparationFailure:'):],
                      'shared four-source-hash QA installation guard unchanged')
        check(len(method_bodies(new))==3,'exact three methods in '+name)
        nine_total+=len(method_bodies(new))
    check(nine_total+len(new_methods)==19,'exact nineteen native test methods, no additions/skips/retries')
    for filename in nine_names[:2]:
        t=(QA/'UITests'/filename).read_text()
        check('try app.performAccessibilityAudit(for: [.contrast, .textClipped, .dynamicType])' in t and
              'issueHandler' not in t and 'stateTimeout: TimeInterval = 3' in t and
              'let limit = Int(ceil(distance / step)) + 2' in t and 'limit <= 64' in t and
              'gestureCount < 168' in t and 'try finishBudget(budget)' in t and
              'if abs(error) <= 2 { restored = true; break }' in t and
              'Reading made no new continuous progress' in t and
              'A reveal gesture skipped an unobserved text region' in t,
              'unchanged unfiltered audits, continuous coverage and explicit bounded R7 geometry policy '+filename)
    for name,pin in EXPECTED_PRODUCT.items():
        check(sha(ROOT/APP/name)==pin,'exact reviewed shipping product bytes '+name)
    check((ROOT/APP/'HalalAnalyzer______________App.swift').read_bytes()==(EVIDENCE/'Baseline-AppEntry.swift.txt').read_bytes(),
          'shipping SwiftUI app entry byte-identical')
    shipping=parse((ROOT/(APP+'.xcodeproj/project.pbxproj')).read_text())
    baseline=parse((EVIDENCE/'Baseline-project.pbxproj.txt').read_text())
    stripped=copy.deepcopy(shipping);stripped['objects'][stripped['rootObject']]['knownRegions'].remove('ar')
    check(stripped==baseline,'production project changes only add Arabic to known regions')
    so=shipping['objects'];sp=so[shipping['rootObject']]
    check(sp['knownRegions']==['en','ar','Base'],'production en/ar/Base region declaration')
    check(len(sp['targets'])==1,'shipping project retains exactly one production target')
    st=so[sp['targets'][0]]
    check(len(st['fileSystemSynchronizedGroups'])==1 and
          so[st['fileSystemSynchronizedGroups'][0]]['path']==APP,
          'reviewed product files and localized resources belong to actual synchronized shipping target')
    check(not st['dependencies'] and not st['packageProductDependencies'],
          'shipping target has no QA dependency, ads package or new external dependency')
    for config in so[st['buildConfigurationList']]['buildConfigurations']:
        setting=so[config]['buildSettings']
        check(setting['PRODUCT_BUNDLE_IDENTIFIER']=='HalalTag.v1.1' and setting['DEVELOPMENT_TEAM']=='WY272L3F3N' and
              setting['CODE_SIGN_STYLE']=='Automatic' and setting['MARKETING_VERSION']=='1.0' and
              setting['CURRENT_PROJECT_VERSION']=='1' and setting['TARGETED_DEVICE_FAMILY']=='1,2',
              'production identity/signing/version/device-family preserved '+so[config]['name'])
    check(not any(re.search(r'AppearanceQA|HALALTAG_UI_QA|--appearance-|--language-launch|CommandLine.arguments|QAInstallation',p.read_text())
                  for p in (ROOT/APP).glob('*.swift')),'no QA host, launch flags or receipt plumbing in shipping Swift')
    check(set(p.name for p in (ROOT/APP).glob('*.swift'))=={'ContentView.swift','IngredientScreening.swift','ScreeningLocalization.swift','HalalAnalyzer______________App.swift'},
          'exact four shipping Swift files')
    for locale in ['en','ar']:
        resource=ROOT/APP/(locale+'.lproj')/'InfoPlist.strings'
        check(resource.is_file() and '"CFBundleDisplayName" = "HalalTag";' in resource.read_text(),
              'real localized shipping bundle resource '+locale)
    privacy=plistlib.loads((ROOT/APP/'PrivacyInfo.xcprivacy').read_bytes())
    check(privacy=={'NSPrivacyTracking':False,'NSPrivacyTrackingDomains':[],'NSPrivacyCollectedDataTypes':[],
        'NSPrivacyAccessedAPITypes':[{'NSPrivacyAccessedAPIType':'NSPrivacyAccessedAPICategoryUserDefaults','NSPrivacyAccessedAPITypeReasons':['CA92.1']}]},
        'no tracking/collection and exact app-local language-preference privacy reason')
    q=parse((QA/'HalalTagQA.xcodeproj/project.pbxproj').read_text());o=q['objects'];pr=o[q['rootObject']]
    def refs(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if re.fullmatch('[0-9A-F]{24}',k):yield k
                yield from refs(v)
        elif isinstance(value,list):
            for v in value:yield from refs(v)
        elif isinstance(value,str) and re.fullmatch('[0-9A-F]{24}',value):yield value
    check(all(r in o for r in refs(q)),'all QA project object references resolve')
    check(not any(v['isa'] in {'PBXShellScriptBuildPhase','XCRemoteSwiftPackageReference','XCSwiftPackageProductDependency'} for v in o.values()),
          'no QA shell build phases or external packages')
    paths={}
    def walk(ident,parent):
        obj=o[ident]
        if obj['isa']=='PBXGroup':
            directory=parent/obj.get('path','')
            for child in obj['children']:walk(child,directory)
        elif obj['isa']=='PBXVariantGroup':
            paths[ident]=[]
            for child in obj['children']:
                walk(child,parent);paths[ident].append(paths[child])
        elif obj['isa']=='PBXFileReference' and obj['sourceTree'] in ['<group>','SOURCE_ROOT']:
            p=((QA if obj['sourceTree']=='SOURCE_ROOT' else parent)/obj['path']).resolve()
            check(p.is_relative_to(ROOT) and p.is_file() and not p.is_symlink(),'QA file reference resolves within owned production clone '+obj['path'])
            paths[ident]=p
    walk(pr['mainGroup'],QA)
    targets={o[t]['name']:o[t] for t in pr['targets']}
    check(set(targets)=={'HalalTagQA','HalalTagQAUItests'},'exact separate QA host and UI-test target inventory')
    def membership(name,kind):
        result=[]
        for pid in targets[name]['buildPhases']:
            phase=o[pid]
            if phase['isa']==kind:
                for b in phase['files']:
                    p=paths[o[b]['fileRef']];result.extend(p if isinstance(p,list) else [p])
        return result
    check(set(membership('HalalTagQA','PBXSourcesBuildPhase'))==
          {QA/'App/HalalTagQAApp.swift'}|{ROOT/APP/n for n in ['ContentView.swift','IngredientScreening.swift','ScreeningLocalization.swift']},
          'QA compiles actual shipping source references and only its own external entry')
    check(set(membership('HalalTagQA','PBXResourcesBuildPhase'))==
          {ROOT/APP/'PrivacyInfo.xcprivacy'}|{ROOT/APP/(l+'.lproj/InfoPlist.strings') for l in ['en','ar']},
          'QA copies actual production privacy and en/ar bundle resources')
    check(set(membership('HalalTagQAUItests','PBXSourcesBuildPhase'))==
          {QA/'UITests'/n for n in nine_names+['HalalTagFunctionalUITests.swift']},'exact four UI-test source memberships')
    check(membership('HalalTagQAUItests','PBXResourcesBuildPhase')==[QA/'UITests/HalalTagSyntheticQAInstallation.json'],
          'installation configuration exists only in UI-test resource target')
    configs=[o[c]['buildSettings'] for x in [pr,*targets.values()] for c in o[x['buildConfigurationList']]['buildConfigurations']]
    check(all(o[x['buildConfigurationList']]['defaultConfigurationName']=='Debug' and len(o[x['buildConfigurationList']]['buildConfigurations'])==1 for x in [pr,*targets.values()]),
          'QA has only Debug configuration')
    check(configs[0]['SUPPORTED_PLATFORMS']=='iphonesimulator' and configs[0]['SDKROOT']=='iphonesimulator' and configs[0]['CODE_SIGNING_ALLOWED']=='NO',
          'QA is simulator-only and signing disabled')
    check(configs[1]['PRODUCT_BUNDLE_IDENTIFIER']==QAID and configs[2]['PRODUCT_BUNDLE_IDENTIFIER']==QAID+'.uitests' and
          configs[1]['SKIP_INSTALL']==configs[2]['SKIP_INSTALL']=='YES','QA identities distinct and neither target installs in an archive')
    scheme=ET.parse(QA/'HalalTagQA.xcodeproj/xcshareddata/xcschemes/HalalTagQA.xcscheme').getroot()
    check(all(e.attrib['buildForArchiving']=='NO' for e in scheme.findall('./BuildAction/BuildActionEntries/BuildActionEntry')) and scheme.find('ArchiveAction') is None,
          'QA scheme has no archive action and no archive build entries')
    check((ROOT/(APP+'.xcodeproj/xcshareddata/xcschemes/'+APP+'.xcscheme')).read_bytes()==(EVIDENCE/'Baseline-ShippingScheme.xcscheme.txt').read_bytes(),
          'shipping archive scheme byte-identical and has no QA references')
    manifest=json.loads((QA/'UITests/HalalTagSyntheticQAInstallation.json').read_text())
    check(manifest['configurationStatus']=='UNCONFIGURED' and not manifest['installationIsDedicatedAndSynthetic'] and
          all(manifest[k] is None for k in ['runID','qaBundleIdentifier','productionBundleIdentifier','uiTestBundleIdentifier','qaArtifactSHA256','buildEvidenceReference','installationEvidenceReference','destinationEvidenceReference']),
          'test launch remains fail-closed with no invented installation or native evidence')
    for key,name in [('contentViewSHA256','ContentView.swift'),('ingredientScreeningSHA256','IngredientScreening.swift'),('screeningLocalizationSHA256','ScreeningLocalization.swift'),('privacyManifestSHA256','PrivacyInfo.xcprivacy')]:
        check(manifest[key]==EXPECTED_PRODUCT[name],'test guard binds exact production file '+name)
    plan=json.loads((QA/'nineteen-case-plan.json').read_text());cases=plan['cases']
    check(plan['scope']=='halaltag-production-composition-nineteen-journeys-r7' and plan['case_count']==len(cases)==19,
          'distinct nineteen-case scope, not the nine-case acknowledgment')
    check(len({c['execution_id'] for c in cases})==19 and len({(c['test_class'],c['method']) for c in cases})==19,
          'nineteen unique execution paths and selectors')
    check([c['method'] for c in cases[3:13]]==list(old_methods) and all(c['group']=='functional' for c in cases[3:13]),
          'original ten retain their reviewed relative source order after English receipt reservation')
    check([c['group'] for c in cases[:3]]==['en','en','en'] and all(c['group']!='en' for c in cases[3:]),
          'original no-UUID English host receipts are reserved before supplementary UUID directories')
    check(sum(c['expected_launches'] for c in cases)==20 and sum(c['expected_launches'] for c in cases if c['group']!='en')==17,
          'twenty process launches and seventeen supplementary UUID paths are required')
    check(all(c['style']=='light' and c['size']=='large' and c['case_id']=='light-large' for c in cases if c['group'] in ['functional','state']),
          'functional and state methods each require actual Light and Large setting readbacks')
    check(plan['old_receipts_valid_for_this_scope'] is False and plan['retry_count']==0,
          'old native receipts and silent retries cannot satisfy new scope')
    check('UserDefaults' not in (QA/'App/HalalTagQAApp.swift').read_text() and 'preferenceKey' not in (QA/'App/HalalTagQAApp.swift').read_text(),
          'QA host never forces language or restores draft/result state')
    icons=[]
    for p in sorted((ROOT/APP/'Assets.xcassets/AppIcon.appiconset').glob('*.png')):
        raw=p.read_bytes();check(raw[:8]==b'\x89PNG\r\n\x1a\n' and raw[12:16]==b'IHDR','icon is a PNG '+p.name)
        width,height,depth,color=struct.unpack('>IIBB',raw[16:26]);has_transparency=color in [4,6]
        offset=8
        while offset<len(raw):
            length=struct.unpack('>I',raw[offset:offset+4])[0];kind=raw[offset+4:offset+8]
            if kind==b'tRNS':has_transparency=True
            offset+=length+12
        icons.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'width':width,'height':height,
                      'bit_depth':depth,'color_type':color,'has_alpha_or_transparency_chunk':has_transparency})
    return {'status':'PASS_SOURCE_STRUCTURE_ONLY','checks_passed':len(checks),'checks':checks,
        'original_ten_method_hashes':{n:hashlib.sha256(v.encode()).hexdigest() for n,v in old_methods.items()},
        'product_hashes':EXPECTED_PRODUCT,'icon_headers':icons,
        'original_ten_entire_file_unchanged':False,'original_ten_bodies_unchanged':True,
        'native_compilation':'NOT_RUN','native_tests':'NOT_RUN','archive':'NOT_RUN',
        'claim_limit':'These checks validate source composition and target structure, not native behavior or contrast.'}
if __name__=='__main__':print(json.dumps(main(),indent=2,ensure_ascii=False))
