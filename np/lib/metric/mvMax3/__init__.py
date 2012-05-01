'Compute the maximum length of medium voltage line for which grid extension is cheaper than standalone options'
# Import custom modules
from np.lib.variable_store import VariableStore as VS, Variable as V
from np.lib import store
import finance
import demographics
import demand
import costDistribution
import costOffGrid
import costMiniGrid
import costGrid



# Variable

class Metric(V):
    'Maximum length of medium voltage line for which grid extension is cheaper than standalone options'

    section = 'metric'
    option = 'maximum length of medium voltage line extension'
    aliases = ['mvmax']
    dependencies = [
        costOffGrid.OffGridSystemNodalDiscountedCost,
        costOffGrid.OffGridSystemNodalLevelizedCost,
        costMiniGrid.MiniGridSystemNodalDiscountedCost,
        costMiniGrid.MiniGridSystemNodalLevelizedCost,
        costGrid.GridInternalSystemNodalDiscountedCost,
        costGrid.GridInternalSystemNodalLevelizedCost,
        costGrid.GridExternalSystemNodalDiscountedCostPerMeter,
    ]
    units = 'meters'

    def compute(self):
        # Compute levelized costs
        self.get(costOffGrid.OffGridSystemNodalLevelizedCost)
        self.get(costMiniGrid.MiniGridSystemNodalLevelizedCost)
        self.get(costGrid.GridInternalSystemNodalLevelizedCost)
        # Compute the cost of the cheapest standalone option for the node
        standaloneCost = min(
            self.get(costOffGrid.OffGridSystemNodalDiscountedCost),
            self.get(costMiniGrid.MiniGridSystemNodalDiscountedCost))
        # Compute the (non-negative) amount of money we have left to spend on grid extension
        gridExternalBudget = max(0, standaloneCost - self.get(costGrid.GridInternalSystemNodalDiscountedCost))
        # Compute the length of line we are allowed for grid extension
        return gridExternalBudget / float(self.get(costGrid.GridExternalSystemNodalDiscountedCostPerMeter))


class System(V):

    section = 'metric'
    option = 'system'
    aliases = ['system']
    c = dict(parse=str)
    dependencies = [
        demand.ProjectedNodalDemandPerYear,
        costMiniGrid.MiniGridSystemNodalDiscountedCost,
        costOffGrid.OffGridSystemNodalDiscountedCost,
    ]

    def compute(self):
        # If the demand is positive,
        if self.get(demand.ProjectedNodalDemandPerYear) == 0:
            return 'unelectrified'
        # If grid is chosen,
        elif self.state[0].isNodeConnected(self.state[1]):
            return 'grid'
        # If mini-grid is chosen,
        elif self.get(costMiniGrid.MiniGridSystemNodalDiscountedCost) < self.get(costOffGrid.OffGridSystemNodalDiscountedCost):
            return 'mini-grid'
        # If off-grid is chosen,
        else:
            return 'off-grid'



# Aggregate


class OffGridSystemTotalDiscountedDemand(V):

    section = 'system (off-grid)'
    option = 'system total discounted demand'
    aliases = ['og_dem_d']
    default = 0
    units = 'kilowatt-hours'

    def aggregate(self, childVS):
        # If the system is off-grid,
        if childVS.get(System)[0] == 'o':
            # Update
            self.value += childVS.get(demand.ProjectedNodalDiscountedDemand)


class OffGridSystemTotalDiscountedCost(V):

    section = 'system (off-grid)'
    option = 'system total discounted cost'
    aliases = ['og_tot_d']
    default = 0
    units = 'dollars'

    def aggregate(self, childVS):
        # If the system is off-grid,
        if childVS.get(System)[0] == 'o':
            # Update
            self.value += childVS.get(costOffGrid.OffGridSystemNodalDiscountedCost)


class OffGridSystemTotalLevelizedCost(V):

    section = 'system (off-grid)'
    option = 'system total levelized cost'
    aliases = ['og_tot_lev']
    dependencies = [
        OffGridSystemTotalDiscountedDemand,
        OffGridSystemTotalDiscountedCost,
    ]
    units = 'dollars per kilowatt-hour'

    def compute(self):
        if self.get(OffGridSystemTotalDiscountedDemand) == 0:
            return 0
        return self.get(OffGridSystemTotalDiscountedCost) / float(self.get(OffGridSystemTotalDiscountedDemand))


class MiniGridSystemTotalDiscountedDemand(V):

    section = 'system (mini-grid)'
    option = 'system total discounted demand'
    aliases = ['mg_dem_d']
    default = 0
    units = 'kilowatt-hours'

    def aggregate(self, childVS):
        # If the system is mini-grid,
        if childVS.get(System)[0] == 'm':
            # Update
            self.value += childVS.get(demand.ProjectedNodalDiscountedDemand)


class MiniGridSystemTotalDiscountedCost(V):

    section = 'system (mini-grid)'
    option = 'system total discounted cost'
    aliases = ['mg_tot_d']
    default = 0
    units = 'dollars'

    def aggregate(self, childVS):
        # If the system is mini-grid,
        if childVS.get(System)[0] == 'm':
            # Update
            self.value += childVS.get(costMiniGrid.MiniGridSystemNodalDiscountedCost)


class MiniGridSystemTotalLevelizedCost(V):

    section = 'system (mini-grid)'
    option = 'system total levelized cost'
    aliases = ['mg_tot_lev']
    dependencies = [
        MiniGridSystemTotalDiscountedDemand,
        MiniGridSystemTotalDiscountedCost,
    ]
    units = 'dollars per kilowatt-hour'

    def compute(self):
        if self.get(MiniGridSystemTotalDiscountedDemand) == 0:
            return 0
        return self.get(MiniGridSystemTotalDiscountedCost) / float(self.get(MiniGridSystemTotalDiscountedDemand))


class GridSystemTotalDiscountedDemand(V):

    section = 'system (grid)'
    option = 'system total discounted demand'
    aliases = ['gr_dem_d']
    default = 0
    units = 'kilowatt-hours'

    def aggregate(self, childVS):
        # Get
        childDataset = childVS.state[0]
        childNode = childVS.state[1]
        # If the system is grid and we are connecting a node that was not in the existing grid,
        if childVS.get(System)[0] == 'g' and not childDataset.wasNodeAlreadyConnected(childNode):
            # Update
            self.value += childVS.get(demand.ProjectedNodalDiscountedDemand)


class GridSystemTotalDiscountedCost(V):

    section = 'system (grid)'
    option = 'system total discounted cost'
    aliases = ['gr_tot_d']
    default = 0
    units = 'dollars'

    def aggregate(self, childVS):
        # Get
        childDataset = childVS.state[0]
        childNode = childVS.state[1]
        # If the system is grid and we are connecting a node that was not in the existing grid,
        if childVS.get(System)[0] == 'g' and not childDataset.wasNodeAlreadyConnected(childNode):
            # Get internal cost
            internalCost = childVS.get(costGrid.GridInternalSystemNodalDiscountedCost)
            # Get half the length of all new connections to the node
            newConnections = childDataset.cycleConnections(childNode, is_existing=False)
            newConnectionLengthHalved = sum(x.weight for x in newConnections) / 2.
            # Get external cost
            externalCostPerMeter = childVS.get(costGrid.GridExternalSystemNodalDiscountedCostPerMeter)
            externalCost = externalCostPerMeter * newConnectionLengthHalved
            # Add internal and external cost
            self.value += internalCost + externalCost


class GridSystemTotalLevelizedCost(V):

    section = 'system (grid)'
    option = 'system total levelized cost'
    aliases = ['gr_tot_lev']
    dependencies = [
        GridSystemTotalDiscountedDemand,
        GridSystemTotalDiscountedCost,
    ]
    units = 'dollars per kilowatt-hour'

    def compute(self):
        if self.get(GridSystemTotalDiscountedDemand) == 0:
            return 0
        return self.get(GridSystemTotalDiscountedCost) / float(self.get(GridSystemTotalDiscountedDemand))


class GridSystemTotalInternalInitialCost(V):

    section = 'system (grid)'
    option = 'system total internal initial cost'
    aliases = ['gr_tot_int_init']
    default = 0
    units = 'dollars'

    def aggregate(self, childVS):
        # Get
        childDataset = childVS.state[0]
        childNode = childVS.state[1]
        # If the system is grid and we are connecting a node that was not in the existing grid,
        if childVS.get(System)[0] == 'g' and not childDataset.wasNodeAlreadyConnected(childNode):
            # Get internal cost
            internalCost = childVS.get(costGrid.GridInternalSystemInitialCost)
            # Add up internal cost
            self.value += internalCost


class GridSystemTotalInternalRecurringCostPerYear(V):

    section = 'system (grid)'
    option = 'system total internal recurring cost per year'
    aliases = ['gr_tot_int_recur']
    default = 0
    units = 'dollars per year'

    def aggregate(self, childVS):
        # Get
        childDataset = childVS.state[0]
        childNode = childVS.state[1]
        # If the system is grid and we are connecting a node that was not in the existing grid,
        if childVS.get(System)[0] == 'g' and not childDataset.wasNodeAlreadyConnected(childNode):
            # Get internal cost
            internalAnnualCost = childVS.get(costGrid.GridInternalSystemRecurringCostPerYear)
            # Add up internal cost
            self.value += internalAnnualCost


class GridSystemTotalInitialCost(V):

    section = 'system (grid)'
    option = 'system total initial cost'
    aliases = ['gr_tot_init']
    dependencies = [
        GridSystemTotalInternalInitialCost,
        costGrid.GridExternalSystemInitialCostPerMeter,
    ]
    units = 'dollars'

    def compute(self):
        #Major Assumption:  GridExternalSystemInitialCostPerMeter is the same
        #across the entire system (vs per node)
        totalSystemMeters = self.state[0].sumNetworkWeight(is_existing=False)
        return self.get(GridSystemTotalInternalInitialCost) + \
            (self.get(costGrid.GridExternalSystemInitialCostPerMeter) * \
             totalSystemMeters)


class GridSystemTotalRecurringCost(V):

    section = 'system (grid)'
    option = 'system total recurring cost'
    aliases = ['gr_tot_recur']
    dependencies = [
        GridSystemTotalInternalRecurringCostPerYear,
        costGrid.GridExternalSystemRecurringCostPerMeterPerYear,
        finance.TimeHorizon,
    ]
    units = 'dollars'

    def compute(self):
        #TODO:  Address below...(may need to use an 'aggregate' function
        #Major Assumption the following are the same across all nodes:  
        # GridExternalSystemRecurringCostPerMeterPerYear
        # DiscountedCashFlowFactor 
        totalSystemMeters = self.state[0].sumNetworkWeight(is_existing=False)
        dcff = self.get(finance.DiscountedCashFlowFactor)
        intlCostPerYear = self.get(GridSystemTotalInternalRecurringCostPerYear)
        extlCostPerYear = totalSystemMeters * \
                self.get(costGrid.GridExternalSystemRecurringCostPerMeterPerYear)
        return (dcff * (intlCostPerYear + extlCostPerYear))

# VariableStore

class VariableStore(VS):

    variableModules = [
        finance,
        demographics,
        demand,
        costDistribution,
        costOffGrid,
        costMiniGrid,
        costGrid,
    ]
    variableClasses = [
        Metric,
        System,
    ]
    aggregateClasses = [
        OffGridSystemTotalDiscountedDemand,
        OffGridSystemTotalDiscountedCost,
        MiniGridSystemTotalDiscountedDemand,
        MiniGridSystemTotalDiscountedCost,
        GridSystemTotalDiscountedDemand,
        GridSystemTotalDiscountedCost,
        GridSystemTotalInternalInitialCost,
        GridSystemTotalInternalRecurringCostPerYear,
    ]
    summaryClasses = [
        OffGridSystemTotalLevelizedCost,
        MiniGridSystemTotalLevelizedCost,
        GridSystemTotalLevelizedCost,
        GridSystemTotalInitialCost,
        GridSystemTotalRecurringCost,
    ]



# Set order

roots = [
    Metric, 
    System, 
    OffGridSystemTotalDiscountedCost,
    OffGridSystemTotalLevelizedCost,
    MiniGridSystemTotalDiscountedCost, 
    MiniGridSystemTotalLevelizedCost,
    GridSystemTotalDiscountedCost, 
    GridSystemTotalLevelizedCost,
    GridSystemTotalInitialCost,
    GridSystemTotalRecurringCost,
]
sections = [
    'finance',
    'demographics',
    'demand',
    'demand (peak)',
    'demand (household)',
    'demand (productive)',
    'demand (social infrastructure)',
    'distribution',
    'system (off-grid)',
    'system (mini-grid)',
    'system (grid)',
    'metric',
]
