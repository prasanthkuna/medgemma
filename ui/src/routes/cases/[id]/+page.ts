import type { PageLoad } from './$types';

export const prerender = false; // Dynamic route
export const ssr = false;

export const load: PageLoad = ({ params }) => {
    return {
        caseId: params.id
    };
};
