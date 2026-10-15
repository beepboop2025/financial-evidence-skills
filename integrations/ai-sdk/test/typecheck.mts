import { financialEvidenceTools, validateSnapshot, queryInputSchema } from '@moomoo202020/financial-evidence-ai-sdk';
import { generateText, isStepCount } from 'ai';
import { MockLanguageModelV4 } from 'ai/test';

const tools = financialEvidenceTools({ synthetic: true });
void generateText({ model: new MockLanguageModelV4(), tools, prompt: 'Compile only', stopWhen: isStepCount(2) });
void tools.financial_evidence_query.execute(queryInputSchema.parse({ dataset: 'money_markets', limit: 3 }), {
  toolCallId: 'compile-only', messages: [], context: {},
});
void validateSnapshot;
