# Scheduling 20 Consultants with Simulated Annealing

**Author:** Francisca Freixo  

A metaheuristic solver for a profit-maximising vehicle-routing and scheduling problem. It decides which of about 1,000 customer orders 20 student consultants should take on, and in what order, within an 8-hour shift.

**Python (standard library only) · simulated annealing · greedy construction · local search**

---

## The problem
- 20 consultants all start and end at headquarters, with a maximum 8-hour shift including driving.
- About 1,000 orders, each with a location, a service time and a profit. Not every consultant is qualified for every order.
- **Objective:** maximise Σ order profit − Σ working time × €60/h.

## Approach
1. **Greedy initialisation**: orders sorted by profit and inserted where they fit best.
2. **Six neighbourhood operators**: add order, remove order, relocate, 2-opt within a route, swap within a route and swap between consultants.
3. **Incremental cost evaluation**, so each move is evaluated in O(1)–O(n) without recomputing whole routes.
4. **Temperature-dependent operator weights**: the search favours adding orders early on and refining routes (2-opt, relocate) as it cools.
5. **Time-based exponential cooling** (T from 40 down to 0.1 over the run), with the best solution saved periodically.

## Result
The solver produced a validated profit of about **€9,400** in a 5-minute run, beating the reference solution. Earlier versions reached €5,000–€8,700. The full write-up, including cooling-schedule experiments and complexity analysis, is in [`docs/METHOD.md`](docs/METHOD.md).

## Running it
```bash
# place drivingtimes.txt and orders.txt in data/
python solver.py 300     # run time in seconds; writes sol.txt
```

*Maastricht University, Modeling & Computing (2026). Problem data was provided by the course.*
