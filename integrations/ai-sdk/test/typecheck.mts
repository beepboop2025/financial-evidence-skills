import { financialEvidenceTools, validateSnapshot, queryInputSchema } from '@moomoo202020/financial-evidence-ai-sdk';
import { generateText, isStepCount } from 'ai';
import { MockLanguageModelV4 } from 'ai/test';
import type { FinancialEvidenceQueryInput } from '@moomoo202020/financial-evidence-ai-sdk';
import { runFinancialWorkflow, financialEvidenceWorkflowTool } from '@moomoo202020/financial-evidence-ai-sdk';

const tools = financialEvidenceTools({ synthetic: true });
void generateText({ model: new MockLanguageModelV4(), tools, prompt: 'Compile only', stopWhen: isStepCount(2) });
void tools.financial_evidence_query.execute(queryInputSchema.parse({ dataset: 'money_markets', limit: 3 }), {
  toolCallId: 'compile-only', messages: [], context: {},
});
void validateSnapshot;

// Defaulted fields remain optional for a typed direct call, as they are at runtime.
const query: FinancialEvidenceQueryInput = { dataset: 'money_markets', limit: 3 };
void tools.financial_evidence_query.execute(query, { toolCallId: 'compile-only', messages: [], context: {} });
// @ts-expect-error Dataset identifiers must remain the published union, not an arbitrary string.
const invalidDataset: FinancialEvidenceQueryInput = { dataset: 'invented_dataset' };
// @ts-expect-error Unknown endpoint parameters are not exposed to callers or models.
const invalidEndpoint: FinancialEvidenceQueryInput = { dataset: 'money_markets', url: 'https://example.test' };
void invalidDataset;
void invalidEndpoint;

void runFinancialWorkflow({workflow: 'funding'}, {synthetic: true});
void generateText({model: new MockLanguageModelV4(),
  tools: {...tools, financial_evidence_workflow: financialEvidenceWorkflowTool()}, prompt: 'Compile only'});
// @ts-expect-error Only the three supported research workflows can be requested.
void runFinancialWorkflow({workflow: 'trade'});
// @ts-expect-error Credentials are never model-facing workflow parameters.
void runFinancialWorkflow({workflow: 'funding', credential: 'private'});
