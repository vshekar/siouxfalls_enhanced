# %%
from __future__ import print_function
import sumolib
from sumolib.visualization import helpers
from optparse import OptionParser
import matplotlib.pyplot as plt
 

# %%
def get_color(value,max_density):
    hues = ['#47ff3a','#a9ff39', '#ffff38', '#ffbf37', '#ff8636', '#ff3535']
    #hues = ['#ff3535', '#ff8636', '#ffbf37', '#ffff38', '#a9ff39', '#47ff3a']
    step = max_density/len(hues)
    color = None
    for i in range(len(hues)):
        if i*step <= value <= (i+1)*step:
            color = hues[i]
            break
        else:
            color = hues[-1]
    return color

def plot(densities, md, net, filename=None):
    args = []
    optParser = OptionParser()
    optParser.add_option("-n", "--net", dest="net", metavar="FILE",
                        help="Defines the network to read")
    optParser.add_option("--edge-width", dest="defaultWidth",
                        type="float", default=0.5, help="Defines the width of not selected edges")
    optParser.add_option("--edge-color", dest="defaultColor",
                        default='#000000', help="Defines the color of not selected edges")
    optParser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                        default=False, help="If set, the script says what it's doing")

    helpers.addInteractionOptions(optParser)
    helpers.addPlotOptions(optParser)
    options, remaining_args = optParser.parse_args(args=args)


    for i,interval in enumerate(densities):
        colors = {}
        widths = {}
        max_density = 0
        min_density = 10000
        for e in interval.keys():
            if max_density < interval[e]:
                max_density = interval[e]
            if min_density > interval[e]:
                min_density = interval[e]

        for e in interval.keys():
            
            colors[e] = get_color(interval[e], md)
            #widths[e] = normalize(interval[e], max_density, min_density) + 2.0
            widths[e] = 4

        fig, ax = helpers.openFigure(options)
        ax.set_aspect("equal", None, 'C')
        helpers.plotNet(net, colors, widths, options)
        lines = ax.get_lines()
        for line in lines:
            line.set_linestyle('--')
        ax.set_title( '{num1:02d}:00:00 to {num2:02d}:00:00 hrs'.format(num1=(i+6)%24,num2=(i+7)%24))
        if filename:
            fig.savefig(f'../output/{filename}.pdf', bbox_inches='tight',pad_inches=0)
        else:
            fig.savefig('../output/hour'+str(i)+'.pdf', bbox_inches='tight',pad_inches=0)
        options.nolegend = True

        helpers.closeFigure(fig, ax, options)

# %%

net = sumolib.net.readNet('../network/SF_combined.net.xml')
densities = [{'1_1': 5}]
max_density = 100
"""
for i in range(24):
    start = i*3600
    #all_sublinks = SESSION.query(LinkStats, SubLinks).filter(LinkStats.sim_num == 1).filter(LinkStats.start_time == start).filter(SubLinks.sublink_id == LinkStats.sublink).all()

    density = {}
    for data in all_sublinks:
        link_name = "{}_{}".format(data[1].link, data[1].sublink)
        density[link_name] = data[0].density
        if data[0].density > max_density:
            max_density = data[0].density
    densities.append(density)
print(len(densities))
"""


plot(densities, max_density, net)

# %%
from result_utils import get_subnet_edges

nodes = {}
for edge in range(1,76):
    total_nodes = len(get_subnet_edges(5, f'{edge}_1', nominal=False, get_nodes=True)[1])
    if total_nodes < 24:
        nodes[edge] = total_nodes
nodes
# %%
nodes
# %%
