import { NodeConnectionTypes, NodeOperationError } from 'n8n-workflow';
import type { IDataObject, IExecuteFunctions, INodeExecutionData, INodeType, INodeTypeDescription } from 'n8n-workflow';

export class FinancialEvidence implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'Financial Evidence', name: 'financialEvidence',
    subtitle: '={{$parameter["dataset"]}}',
    icon: {light: 'file:financialEvidence.svg', dark: 'file:financialEvidence.dark.svg'}, group: ['transform'], version: 1,
    description: 'Get source-cited research with dates, units and coverage limits',
    defaults: { name: 'Financial Evidence' },
    inputs: [NodeConnectionTypes.Main], outputs: [NodeConnectionTypes.Main],
    usableAsTool: true,
    properties: [
      {displayName: 'Dataset', name: 'dataset', type: 'options', default: 'money_markets', options: [
        {name: 'Bank Risk', value: 'bank_risk'}, {name: 'Capital Markets', value: 'capital_markets'},
        {name: 'China Economy', value: 'china_economy'}, {name: 'Market Liquidity', value: 'market_liquidity'},
        {name: 'Money Market History', value: 'money_market_history'}, {name: 'Money Markets', value: 'money_markets'},
        {name: 'Source Health', value: 'source_health'},
      ]},
      {displayName: 'Entity', name: 'entity', type: 'string', default: '', description: 'Optional entity ID or name filter (up to 100 characters)'},
      {displayName: 'Limit', name: 'limit', type: 'number', default: 50, typeOptions: {minValue: 1, maxValue: 100}, description: 'Max number of results to return'},
      {displayName: 'Offset', name: 'offset', type: 'number', default: 0, typeOptions: {minValue: 0, maxValue: 100000}, description: 'Use next_offset from the previous response for the next page'},
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const output: INodeExecutionData[] = [];
    const datasets = ['bank_risk', 'capital_markets', 'china_economy', 'market_liquidity', 'money_market_history', 'money_markets', 'source_health'];
    for (let i = 0; i < this.getInputData().length; i++) {
      try {
        const dataset = this.getNodeParameter('dataset', i) as string;
        const entity = this.getNodeParameter('entity', i) as string;
        const limit = this.getNodeParameter('limit', i) as number;
        const offset = this.getNodeParameter('offset', i) as number;
        if (!datasets.includes(dataset) || typeof entity !== 'string' || entity.length > 100 ||
            !Number.isInteger(limit) || limit < 1 || limit > 100 ||
            !Number.isInteger(offset) || offset < 0 || offset > 100000) {
          throw new NodeOperationError(this.getNode(), 'Choose a supported dataset, entity up to 100 characters, limit 1–100 and offset 0–100000', {itemIndex: i});
        }
        const result = await this.helpers.httpRequest({
          method: 'GET', url: 'https://api.seiche.info/openbb/api/v1/query',
          qs: {dataset, entity, limit, offset}, json: true, timeout: 30000,
          headers: {Accept: 'application/json'},
        }) as IDataObject;
        if (!result || result.schema !== 'liquidity-lab.openbb-table.v1' || result.dataset !== dataset ||
            !Array.isArray(result.results) || !Array.isArray(result.sources) || !Array.isArray(result.diagnostics) ||
            !Object.prototype.hasOwnProperty.call(result, 'next_offset')) {
          throw new NodeOperationError(this.getNode(), 'Unexpected research response; inspect the API contract before continuing', {itemIndex: i});
        }
        // One page per item keeps source diagnostics attached to every result.
        output.push({json: result, pairedItem: {item: i}});
      } catch (error) {
        if (this.continueOnFail()) {
          output.push({json: {error: error instanceof Error ? error.message : 'Research request failed'}, pairedItem: {item: i}});
        } else {
          throw new NodeOperationError(this.getNode(), error as Error, {itemIndex: i});
        }
      }
    }
    return [output];
  }
}
