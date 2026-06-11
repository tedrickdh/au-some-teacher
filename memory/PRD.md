# Au-Some Teacher ABA Services Website Redesign PRD

## Original Problem Statement
Redesign https://www.au-someteacher.com/ into a premium, modern, mobile-first website for Au-Some Teacher ABA Services, an in-home ABA therapy company serving children with autism throughout Greater Houston, including Spring, Klein, The Woodlands, Conroe, Humble, Tomball, and Magnolia. The site should feel clean, warm, professional, trustworthy, education-informed, and conversion-focused, using Deep Navy #163A5F, Teal #2CB1BC, Warm Gold #F4B942, white, and soft gray. Required pages: Home, Services, Insurance, About Us, Careers, Become a Client. Required homepage sections: hero, insurance, parent connection, services, process, why choose us, team, testimonials, FAQ, and final CTA.

## Architecture Decisions
- Frontend: React SPA with React Router routes for all requested pages.
- Styling: Tailwind CSS with custom brand tokens, Outfit headings, DM Sans body font, Shadcn UI primitives, lucide-react icons.
- Backend: FastAPI with MongoDB via existing MONGO_URL and DB_NAME environment variables.
- Lead capture: POST /api/leads stores parent, insurance, and career inquiry submissions in MongoDB.
- Configuration: Frontend uses REACT_APP_BACKEND_URL; backend CORS origins are environment-driven and restricted to the preview URL.

## Implemented
- Premium responsive marketing site with complete homepage and all requested page templates.
- Desktop navigation, mobile sheet menu, dropdown service links, footer navigation, CTA routing.
- Homepage sections: hero, insurance cards, compassionate parent section, services cards, 4-step process, why families choose us, leadership profile, testimonials, FAQ accordion, final CTA.
- Services, Insurance, About Us, Careers, and Become a Client pages.
- Lead forms for client intake, insurance verification, and careers with success/error toasts.
- Backend lead submission endpoint with validation and MongoDB persistence.
- Test coverage: frontend/browser flows validated; backend regression tests added for /api/leads.

## Verification
- JavaScript lint passed.
- Python lint passed.
- Frontend production build passed.
- Backend pytest lead API tests passed: 3/3.
- Browser checks passed for desktop/mobile routing, FAQ, form submission, and no mobile horizontal overflow.
- Testing agent completed with 100% frontend and backend success.

## Prioritized Backlog
### P0
- Replace placeholder professional photography/headshot with final approved brand photography.
- Confirm final business phone/address if needed and add to footer/forms.

### P1
- Add email notification or CRM integration for lead submissions.
- Add SEO metadata per route and structured local business/medical organization schema.
- Add dedicated detail anchors or subpages for each service.

### P2
- Add social proof expansion: insurance badges, provider referral section, downloadable intake checklist.
- Add careers application fields/resume upload if recruiting workflow requires it.
- Add analytics conversion tracking for form submissions and CTA clicks.


## Code Review Fixes Applied
- Fixed toast hook subscription effect dependencies by extracting listener subscription cleanup.
- Refactored long Header and LeadForm responsibilities into smaller navigation, menu, field, and form-hook helpers.
- Added Python type hints to backend route handlers and lead API regression tests.
- Re-verified with frontend lint, backend lint, production build, pytest lead API regression tests, and browser smoke test.
