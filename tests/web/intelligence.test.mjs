import {test} from 'node:test';
import assert from 'node:assert/strict';
import {learningReport,learning,workbench} from '../../src/web/static/intelligence.js';
const report={metrics:{ridge:{mae:4,wape:null,bias_units:2},recent_7d:{mae:2,wape:.2,bias_units:1},same_weekday:{mae:3,wape:.3,bias_units:1}},empirical_interval:{observed_test_coverage:.2},holdout:[{day:'2026-09-01',actual:5,predicted:7,lower:3,upper:11}],split:{test:{start:'2026-09-01',end:'2026-09-28',usable_days:25}},warnings:['<img src=x onerror=alert(1)>'],beats_both_baselines:false,origin:'synthetic',model_version:'v1',dataset_sha256:'abc',selected_alpha:1,excluded_stockout_days:2};
test('model failure remains visible and cannot be described as ready for deployment',()=>{const html=learningReport(report);assert.match(html,/Fails baseline comparison/);assert.match(html,/Do not promote/);assert.match(html,/research only/);});
test('model report escapes imported text and displays missing percentage as unavailable',()=>{const html=learningReport(report);assert.ok(!html.includes('<img src=x'));assert.match(html,/&lt;img/);assert.ok(!html.includes('<td>0.0%<\/td>'));});
test('learning and operational views explain their separate responsibilities',()=>{assert.match(learning(),/separate from operational/);assert.match(learning(),/No trained model/);assert.match(workbench(),/evidence behind every decision/);});
