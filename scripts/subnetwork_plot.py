# %%
import networkx as nx
import json
import matplotlib.pyplot as plt
import os
import plotly.graph_objs as go
# %%
print(os.getcwd())
node_loc = json.load(open('../network/node_locations.json'))
edge_con = json.load(open('../network/edge_connections.json'))

G = nx.DiGraph()

for edge in edge_con:
    edge[0] = str(edge[0])
    edge[1] = str(edge[1])
    

def full_net(G):
    G.add_edges_from(edge_con)
    return G

    
def lmbd1_net():
    nodes = ["5", "9", "4", "6", "8", "10"]
    for edge in edge_con:
        if edge[0] in nodes and edge[1] in nodes:
            G.add_edge(edge[0], edge[1])

def lmbd2_net():
    nodes = ["5", "9", "4", "6", "8", "10", "3", "11", "15", "17", "16", "7", "2" ]
    for edge in edge_con:
        if edge[0] in nodes and edge[1] in nodes:
            G.add_edge(edge[0], edge[1])

def lmbd3_net():
    nodes = ["5", "9", "4", "6", "8", "10", "3", "11", "15", "17", "16", "7", "2", "1", "12", "14", "22", "19", "18" ]
    for edge in edge_con:
        if edge[0] in nodes and edge[1] in nodes:
            G.add_edge(edge[0], edge[1])

# %%            
#lmbd3_net()         
G = full_net(G)   
nx.draw_networkx(G, pos=node_loc, with_labels=True, font_color='w', node_size=1300, font_size=12, width=5, arrows=False)
plt.rcParams["figure.figsize"] = 11,10
plt.draw()
plt.axis('off')

plt.show()
for node in node_loc:
    G.nodes[node]['x'] = node_loc[node][0]
    G.nodes[node]['y'] = node_loc[node][1]

nx.write_graphml(G, 'test.graphml')


# %%
edge_x = []
edge_y = []
for edge in G.edges():
    x0, y0 = G.nodes[edge[0]]['x'], G.nodes[edge[0]]['y']
    x1, y1 = G.nodes[edge[1]]['x'], G.nodes[edge[1]]['y']
    edge_x.append(x0)
    edge_x.append(x1)
    edge_x.append(None)
    edge_y.append(y0)
    edge_y.append(y1)
    edge_y.append(None)

edge_trace = go.Scatter(
    x=edge_x, y=edge_y,
    line=dict(width=0.5, color='#888'),
    hoverinfo='none',
    colorscale='Bluered',
    mode='lines')

node_x = []
node_y = []
for node in G.nodes():
    x, y = G.nodes[node]['x'], G.nodes[node]['y']
    node_x.append(x)
    node_y.append(y)

node_trace = go.Scatter(
    x=node_x, y=node_y,
    mode='markers',
    hoverinfo='text',
    marker=dict(
        showscale=True,
        # colorscale options
        #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
        #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
        #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
        colorscale='YlGnBu',
        reversescale=True,
        color=[],
        size=10,
        colorbar=dict(
            thickness=15,
            title='Node Connections',
            xanchor='left',
            titleside='right'
        ),
        line_width=2))

#%%
fig = go.Figure(data=[edge_trace, node_trace],
             layout=go.Layout(
                title='<br>Network graph made with Python',
                titlefont_size=16,
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20,l=5,r=5,t=40),
                annotations=[ dict(
                    text="Python code: <a href='https://plotly.com/ipython-notebooks/network-graphs/'> https://plotly.com/ipython-notebooks/network-graphs/</a>",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002 ) ],
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                )
fig.show()
# %%
print(G.edges())
edge_con
# %%