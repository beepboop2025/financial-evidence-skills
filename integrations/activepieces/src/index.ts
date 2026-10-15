import { createPiece } from '@activepieces/pieces-framework';
import { financialEvidenceAuth } from './lib/auth';
import { listResearchDatasets } from './lib/actions/list-datasets';
import { getResearchEvidencePage } from './lib/actions/get-evidence-page';

export const financialEvidence = createPiece({
  displayName: 'Financial Evidence',
  description: 'Source-cited financial research with source dates, native units and coverage limits.',
  logoUrl: 'https://raw.githubusercontent.com/beepboop2025/financial-evidence-skills/main/assets/logo.svg',
  authors: ['beepboop2025'],
  minimumSupportedRelease: '0.95.1',
  auth: financialEvidenceAuth,
  actions: [listResearchDatasets, getResearchEvidencePage],
  triggers: [],
});
