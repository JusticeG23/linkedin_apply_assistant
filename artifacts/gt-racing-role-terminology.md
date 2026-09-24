# GT/endurance racing role terminology research

## Evidence

- [Manthey Racing — (Senior) Race Engineer GT3 job description](https://manthey-racing-gmbh.jobs.personio.de/job/2343956?language): owns engineering for one car and driver; prepares race/test performance plans; manages daily engineering operations and that car's crew with the Crew Chief; collaborates across engineering workgroups. Strong analogue for planning and coordinating work.
- [W Racing Team — Careers](https://www.w-racingteam.com/racing/careers): its #1 Mechanic directs the mechanic crew; Mechanic prepares and builds race cars. Shows hands-on execution roles and distinct coordination vs implementation.
- [FIA WEC — Vincent Vosse: Our goal is to fight at the front](https://www.fiawec.com/en/news/vincent-vosse-our-goal-is-to-fight-at-the-front/8301): identifies Vosse as Team Principal of Team WRT and quotes him describing team objectives and a driver-availability decision. Supports Team Principal as senior leadership/decision analogue, though not a complete formal job description.

## Recommendation

Use neutral software-role labels, with racing analogues only as explanatory context:

| Software role | Recommended label | Racing analogue | Basis |
|---|---|---|---|
| Human decision-maker | **Decision Owner** | Team Principal | Senior team leadership and objectives; human retains approvals and final decisions. |
| Planner/orchestrator | **Coordinator** | Race Engineer | Builds plans, coordinates car/team work, integrates specialist inputs. |
| Implementation/research workers | **Specialists** (e.g. Research Specialist, Implementation Specialist) | Engineers and Mechanics | Distinct analysis/engineering and hands-on execution roles; choose specialization by task. |

Avoid using **Team Principal** and **Race Engineer** as literal agent titles: real responsibilities vary by team, and a race engineer is commonly accountable for a particular car/program. Neutral labels preserve clear software authority boundaries while retaining the racing analogy for explanations. This also avoids naval terminology.

Terminology check: **Race Engineer** and **Specialists** are well supported analogues for orchestration and workers. **Driver** is a weaker analogue for the human decision-maker: in racing, driver means the person operating the car, while the evidence associates senior team leadership and team-level objectives with the Team Principal. For precise software authority, prefer **Decision Owner**; if retaining the racing metaphor, **Team Principal** better signals decision authority than **Driver**.
