import { createAction } from '@activepieces/pieces-framework';
import { financialEvidenceAuth } from '../auth';
import { listDatasets } from '../research';

export const listResearchDatasets = createAction({
  name: 'list_research_datasets',
  displayName: 'List Research Datasets',
  description: 'List public research datasets, coverage descriptions and available filters.',
  auth: financialEvidenceAuth,
  requireAuth: false,
  aiMetadata: { idempotent: true, description: 'Read public dataset descriptions and coverage. This action does not retrieve observations or assess freshness.' },
  props: {},
  async run() { return listDatasets(); },
});
