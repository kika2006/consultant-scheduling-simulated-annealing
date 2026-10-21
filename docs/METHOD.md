# Method: Simulated Annealing for Consultant Scheduling

*Technical report written for the Modeling & Computing course (Maastricht University).*

## Introduction

Student Consulting Services B.V. is a consultancy company consisting of
20 student consultants. The company has received around 1000 orders from
customers, but unfortunately, not all orders can be fulfilled, as each
student can only work an 8-hour shift, not all students are qualified
for do every order, and serving each customer requires travelling to
their location also taking time from 8-hour shift. In this assignment,
we are asked to develop an algorithm that constructs (using simulated
annealing) that will find a schedule (for each student), that maximizes
profit (revenue from orders minus paying students).

The **objective function** of the problem is to maximize profit; this
can be more formally defined as:

**Formula 1:** $Net\ Profit = \sum (order\ profit) - \ \sum (student\ working\ time\  \times \frac{€60}{hr})$
,

It is also essential to define soft and hard constraints before starting
to find a solution, as these are essential to understand what it is what
the problem requires. The following are the **hard constraints**; these
are aspects that must be satisfied in any solution that is valid:

- Student total shift duration - in total, including driving from and
  back to the headquarters, each student mustn’t work for more than 8
  hours (28,800 seconds)

- Each order must only be assigned to at most 1 student and visited at
  most once

- A student can only accept/satisfy an order if they are qualified to do
  so - this is given in the problem in the form of a matrix, if 1 = can
  accept, 0 = cannot accept

- Each student’s route must start and end at the headquarters, working
  time includes time spent serving customers and also driving to the
  place of the order.

**Soft constraints** are constraints that don’t need to be met but if
they aren’t the solution gets a punishment. In this problem there aren’t
any specific soft constraints, all the ones specified in the problem are
hard constraints. However, in practice the use of simulated annealing
allows for temporarily infeasible moves to be considered and rejected,
effectively treating the shift-time limit as a hard constraint enforced
at the operator level.

## Algorithm Description

## GREEDY INITIALIZATION

Before applying the process of simulated annealing, we used the greedy
algorithm approach to get an initial starting point. This is done by
processing orders in decreasing order of profit. Then for each order,
the algorithm evaluates all qualified students and all possible
insertion positions within their current routes. It selects the student
and position that create the highest marginal net profit (revenue of
order - additional driving cost incurred by inserting it). An order is
then only inserted if both the hard constraints are satisfied and the
marginal net profit is positive.

We started with the greedy heuristic, as it ensures that the simulated
annealing algorithm starts from a high-quality feasible solution rather
than from scratch, this dramatically reduces running time.

## OPERATORS

When mapping out the problem, we thought about all the different ways we
could change a solution from one state to another. This led us to the
following 6 operators:

- 

- **Add** this is needed in order for the solution to grow, without it
  we couldn’t never add new orders into the solution

- **Remove** this is needed as sometimes freeing up a student’s time to
  make order later, this helps escape the local optima by undoing
  un-optimal earlier decisions

- **Relocate** this fixes misallocation from the greedy initialization
  in a single step, this is helpful as it moves an order from one
  student to another without changing total amount of orders served

- **2-opt intra** this is needed as once the right orders are assigned
  to a student, this is able to fix any un-optimal route orderings
  (crisscrossing)

- **Swap intra** this is very similar to 2-opt intra, as it swaps two
  orders within the same student's route, however it is lighter and less
  impactful

- **Swap Inter** this reassigns two orders between students without
  changing the total served, this is extremely useful when an order is
  cheaper for student B to do than student A

## INCREMENTAL COMPUTATION

All operators we used make use of the incremental updating, this means
that instead of recomputing the entire net profit from scratch after a
move, only the affected edges in the routing graph are recalculated. For
example, inserting or removing an order at position *i* only changes the
edge before it and the edge after it, everything else stays the same.
This makes each delta calculation O(1), regardless of how long the route
is, allowing the algorithm to run approximately 5,000,000 iterations per
second.

## TEMPERATURE

The starting temperature setting determines how exploratory the
simulated annealing is when evaluating worse solutions. As a starting
value, we used **T = 200** (allowed the model to be slightly more
exploratory than 100) with an ending temperature of **T = 0.01**. After
running the algorithm multiple times it produced promising results,
however we believed the algorithm was running inefficiently. We
hypothesized that the time spend at both extremes was too high. At the
start, the high temperatures inflated the acceptance rate, letting the
algorithm allow almost any move regardless of quality, consequently
performing an almost “random” walk. On the other hand, the near-zero
barely allowed any steps, “freezing” it in place. Both extremes wasted
running time and therefore hindered the algorithm to make more
meaningful improvements.

When we began analyzing what could be improve, we saw that T = 200 was
counterproductive given our initialization strategy. Since we built a
starting solution using a greedy algorithm, our model was already a
strong initial profit. By allowing it to explore extreme moves early on,
it actively destroyed the structure already build by the greedy
algorithm rather than improving upon it.

We therefore decided to reduce the starting temperature. We ran the
model multiple times, lowering the temperature incrementally: 200 100 50
30 20. Decreasing the starting temperature consistently improved the
profit, hitting a maximum at T = 30 and T = 20. This led us to try T =
40, which produced the best results overall, as it allowed the model
slightly more exploration to escape a local optimum without reverting to
the destructive randomness of T = 200.

We then turned out attention to the ending temperature of 0.01. We knew
the model was spending a significant portion of running time at
near-zero temperatures where the acceptance rate was rejecting almost
any move. This meant that it was “frozen” a significant portion of
runtime before it elapsed and wasted iterations that could have been
used more productively. We increased T_end from 0.01 to 0.1 which kept
the algorithm slightly warmer at the end and ensured it continued to
make selective improvements throughout the full runtime.

The combination **T_start = 40** and **T_end = 0.1**, was able to
achieve the highest profit.

## OPERATOR SELECTION WEIGHTS 

We initially ran the algorithm with **fixed uniform weights**, so that
each operator had an equal chance of being selected. This quickly showed
that is gave limited results, as we saw the profit was lower than we
hoped for. After some research, we understood that uniform weights make
no distinction between what the algorithm should be doing at different
stages. At an early stage, you want the algorithm to explore and add as
many profitable orders as possible, while later you want to really
fine-tune the route order and fix any misallocations. Treating all
operators equally throughout the whole process ignores this entirely.

We then learnt and tried using **time-based adaptive weights**,
splitting the run into early, mid, and late phases (100 seconds in each
phase) with different probabilities per phase. This surprisingly didn’t
really show any improvement, we believe that the transitions between the
three phases were too abrupt and that the boundaries (of 100 seconds per
phase) were quite arbitrary, the algorithm didn't actually reflect where
it was in the process as we had initially hoped for.

The best results came from **temperature-based adaptive weights**, which
is what we use in our algorithm. Since temperature already measures how
"exploratory" the algorithm is being at any given moment, linking
operator weights to temperature is what best reflects where it is at in
the process. At high temperatures, exploratory operators such as Add
Order and Remove Order get higher weights. At lower temperatures,
improvement operators like 2-opt and Relocate are then more likely to
appear. This gave us the highest profit of the three approaches and also
seemed the approached that most fit the problem.

| Operator     | High T (\>5) | Mid T (0.5–5) | Low T (\<0.5) |
|--------------|--------------|---------------|---------------|
| Add Order    | 50%          | 40%           | 10%           |
| Remove Order | 10%          | 10%           | 5%            |
| Relocate     | 20%          | 30%           | 20%           |
| 2-opt Intra  | 5%           | 20%           | 30%           |
| Swap Intra   | 5%           | 5%            | 10%           |
| Swap Inter   | 10%          | 10%           | 20%           |

## COOLING SCHEDULE 

Before settling on an optimal cooling schedule, we ran multiple tests
with three different approaches.

As recommended by our tutor, we began with the **hyperbolic cooling
schedule**:

**Formula 2:** $T\  = \frac{{\ T}_{start\ }}{\ (iteration\  + \ 1)}$ ,

This method showed very promising result and after tuning we reached
peak profits approaching €20.000. However when validating our solutions
with the checker.py file, we only had a confirmed profit of ~ €5.000.
After checking our code, we identified that when writing the solution
file, incremental floating point additions accumulate tiny rounding
errors over millions of iterations that cause the tracked profit to
drift away from the true value. When fixing this bug, we were unable to
improve the profit beyond approximately €6.500. The fundamental reason
is that with 270,000 iterations per second, the temperature drops to
near zero within milliseconds, leaving the algorithm frozen for the
remaining runtime and reducing it to a simple greedy local search with
no meaningful exploration.

We then moved on to a new method, **two-phase cooling**:

**Formula 3:** $$T\  = \left\{ \begin{array}{r}
T_{1}\  \times \ \left( \frac{T_{2}}{T_{1}} \right)^{frac\text{/}\alpha\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ } \\
T_{2}\  \times \ \left( \frac{T_{3}}{T_{2}} \right)^{(frac - \alpha)\text{/}(1 - \alpha)}
\end{array} \right.\ \binom{if\ frac\  \leq \ \alpha}{if\ frac\  > \ \alpha}\ $$

This method splits the cooling schedule into two distinctive curves, an
exploration phase and an exploitation phase. The algorithm spends the
first 70% of its runtime decreasing the temperature from T = 40 to T =
1, allowing broad exploration, trying different order assignments,
moving orders between students, discovering which combinations work well
together. By the time it reaches T = 1 the algorithm has settled into a
promising region of the solution space.

The remaining 30% is spent cooling from T = 1 to T = 0.1, enabling the
algorithm to spend an extended period at the range where the most
valuable fine-tuning happens. The algorithm is making careful selective
improvements to routing within each student's day, squeezing out the
last euros of profit. This helped us reach a constant profit of
approximately €8.700.

Through experimenting with multiple different cooling schedules,
operator weights and parameter combinations, we recognized that there
was always a way to improve the model just the slightest bit more.

This led us to try **geometric cooling** **schedule**:

**Formula 4:** $frac = \frac{elapsed}{time\_ limit}$
$T = T\_ start\  \times \ \left( \left( \frac{T\_ end}{T\_ start} \right) \right)^{frac}$,

The cooling process uses a constant multiplying factor to reduce the
temperature at each step, resulting in a curve that drops steeply when
temperature is high and slowly when temperature is low. A key advantage
is that it is time-based rather than iteration-based. This addressed the
inconsistencies across our two laptops and deliver the most consistent
results.

The defining characteristic of geometric cooling is that it allocates
runtime proportionally across the temperature range, it falls steeply
when high and slowly when low. For this problem the most valuable
temperature range is roughly T=5 to T=0.5 which keeps the temperature
warm enough to accept occasional worse moves but cold enough to be
selective. The geometric curve spends approximately 55% of its runtime
in this range, compared to approximately 35% for linear cooling.

Combined with the other improvements we made to the operator weights and
starting temperature, this schedule helped us consistently drive the
profit over the €9.000 mark, passing the checker.

## Simulated Annealing

Simulated annealing is the cross-section between random exploration and
greedy algorithms. This is why it is a perfect fit for this problem; it
builds on the greedy solution, exploring and retaining improvements
while occasionally accepting worse solutions to escape local optima.

## STEP 1 – Greedy

Rather than starting from scratch, simulated annealing is able to start
with the structure already produced by the greedy algorithm and
continues to improve upon it. The sorted orders by profit give the
algorithm a good base structure to build upon, rather than wasting time
exploring completely new combinations

## STEP 2 – Define and Evaluate Neighborhood

The neighborhood defines, how the algorithm moves between solutions.
Here we decided upon six different operators that are all able to
address a separate issue that greedy might have overlooked. The
simulated annealing produces very similar solutions, changing the
solution only minimal, calculating the delta for the specific change and
evaluating the incremental update in the neighborhood.

## STEP 3 – Acceptance Decision

If the calculated delta of the move improves the solution, the change is
always accepted. Rejection depends on the current temperature. When a
move worsens profit it is accepted with a probability:

**Formula 5:** $e^{\mathrm{\Delta}/T}$,

Early in the run, the algorithm is more prone to accept a move that
decreases the profit. For example at T = 40, a decrease of 2€ of profit
is accepted 95% of the time, when the temperature drops below 5, this
acceptance rate decreases to 67%. As temperature decreases the algorithm
becomes increasingly selective, eventually accepting only improvements.

## STEP 4 – Temperature Schedule 

As mentioned above, the temperature schedule controls, how exploratory
the algorithm is at different points in time. Starting of very
exploratory and accepting of “bad” moves, the acceptance rate decreases
with a drop in temperature. By the end only the best improving moves are
accepted. We tested three cooling schedules – hyperbolic, two-phase
geometric and single phase geometric – ultimately settling on single
phase geometric cooling from T=40 to T=0.1 as it delivered the most
consistent results.

## STEP 5 – Operator Weights

Not all operators are equally useful at every stage of the run. We use
adaptive operator weights that shift based on the current temperature.
When hot, the algorithm favors add and remove operators to explore
different assignments broadly. When cold it favors 2-opt and swap
operators to fine-tune routing within each student's day.

## STEP 6 – Track Solution

At every stage, the algorithm separates the search process and the best
profit recorded. When the current state exceeds the tracked best, the
best state is saved. The best profit is updated every five minutes with
all corresponding combinations needed to achieve this, ensuring the best
result is preserved even if the algorithm is interrupted before the time
limit is reached

## Complexity Analysis

The greedy initialization has complexity of:

**Formula 6:** $O(O\  \times \ N\  \times \ R)$ ,

Where: O is the number of orders,

N is the number of students (20),

R is the average route length.

In practice, this is at most O(1000 × 20 × \|R\|) ≈ O(20,000 × \|R\|).

## SIMULATED ANNEALING ITERATION

Each simulated annealing iteration consists of:

- Operator selection ---\> O(1) using weighted random choice.

- Delta computation ---\> O(1) for all six operators (incremental edge
  cost update).

- Acceptance decision ---\> O(1) (comparison or exp calculation).

- Apply move ---\> O(1) for swap operators OR O(R) for insert/remove

However, for the apply move, since routes are short in practice and most
moves are rejected before being applied, this is rarely a bottleneck.

In theory, the worst-case per-iteration complexity is O(R) due to the
add/remove operators. In practice however, most iterations either select
a swap operator or get rejected before the move is applied at all,
meaning the O(R) cost is paid only occasionally.

## SPACE COMPLEXITY

The biggest memory cost is storing the driving times between all
locations (252 × 252). The solution itself (the 20 student routes and a
dictionary keeping track of which student is doing which order) takes up
very little memory. The only slightly more expensive memory operation is
copying the best solution found so far, which we do at most every 5
second

## Conclusion

Student Consulting Services B.V. set out to maximise the profit from a
day of consultancy orders, with 20 consultants and time constraints. Our
simulated annealing implementation with a greedy initialization achieves
a profit consistently of around €9,400 exceeding the refence given in
the problem.

The parameters we used to get this result are:

- Starting Temperature ---\> 40.0

- End Temperature ---\> 0.1

- Cooling Schedule ---\> Time-based (exponential)

- Runtime ---\> 300sec (5min)

- Operating Used ---\> 6 operators used

The greedy initialization allowed the algorithm a strong starting point,
and the temperature-based adaptive operator weights ensured a good
equilibrium between exploration and improvement depending on what point
of the learning process it is at. Together with the parameters mentioned
above, allowed us to find a solution which maximized the profit within
the 5-minute time budget.
