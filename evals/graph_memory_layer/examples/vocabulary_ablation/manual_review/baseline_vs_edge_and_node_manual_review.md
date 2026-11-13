# Vocabulary Ablation Manual Review — Baseline vs Edge+Node

Generated: 2026-06-30T20:19:17Z
Model: `gpt-5.4-mini`

## c1s1-stonebridge

Source: evals/graph_memory_layer/examples/session_1_recap_ingest/expected_normalized_recap.md

### `baseline`

- Nodes: 47; edges: 28; cost: $0.046659
- Node recall: 0.7692; edge recall: 0.2917
- Recognition: 0.857 (6/7); contamination: 0/4
- Party anchors inserted: ['baergrom', 'bonogo', 'caelynn', 'ephanna', 'karsemine', 'stafl']
- Party collective inserted: True
- Party membership edges: ['baergrom', 'bonogo', 'caelynn', 'ephanna', 'karsemine', 'stafl']
- Session context warnings: []
- Node kinds: `{'actor': 10, 'collective': 11, 'object': 10, 'place': 11, 'thread': 5}`
- Edge predicates: `{'attacks': 1, 'belongs_to': 1, 'caused_by': 1, 'contains': 3, 'holds': 2, 'leads_to': 2, 'located_in': 2, 'member_of': 7, 'mission_targets': 1, 'part_of': 1, 'same_as': 3, 'serves': 1, 'within': 3}`
- Missing gold nodes: the cat owl, the rat cellar fight, the rat-clearing job, the shatter mage's tower mystery, the giant statue foot, the shatter mage's tower
- Extra candidate nodes: flaming magma infused spider monstrosity, local brewer Glowkindle, merchant guards, Stone Bridge, band of mercenaries, residents of the shatter mages tower, Magma-infused spider monstrosity, The River's Edge Pub, Job board, Enormous boulder / foot of a statue, Magical crystals, Broken alchemical tools, Trapped mosaic, Cat owl, beautifully tiled hallway, clear trail along the river, enormous boulder, room full of broken alchemical tools, shatter mages tower, trapped mosaic, The Wizard's Tower Brewing Company, Room full of broken alchemical tools, Unidentified resident of the shatter mages tower, Trapped mosaic in the hallway, gnomes, job board, The River's Edge Pub
- Missing gold edges: the brewing company is located in the tower, the cat owl is part of the rat cellar fight, the fermentation cellar is in the tower, the rat cellar fight threatens the excavation crew, the excavation crew works for the brewery, Glowkindle operates the Wizard's Tower Brewing Co, Glowkindle posted the rat-clearing job, the troupe of gnomes work at the brewery, Grishna knows where the brewery is located, Grishna operates The River's Edge Pub, the rat-clearing job was posted on the job board, the job board is in Stone Bridge, the heroes / party accept the rat-clearing job, the heroes / party travel to the brewery, The River's Edge Pub is in Stone Bridge, giant rats are in the fermentation cellar, giant rats are part of the rat cellar fight

### `edge_and_node_packet`

- Nodes: 47; edges: 25; cost: $0.042651
- Node recall: 0.6923; edge recall: 0.2917
- Recognition: 1.0 (7/7); contamination: 0/4
- Party anchors inserted: ['baergrom', 'bonogo', 'caelynn', 'ephanna', 'karsemine', 'stafl']
- Party collective inserted: True
- Party membership edges: ['baergrom', 'bonogo', 'caelynn', 'ephanna', 'karsemine', 'stafl']
- Session context warnings: []
- Node kinds: `{'actor': 11, 'collective': 8, 'object': 18, 'place': 5, 'thread': 5}`
- Edge predicates: `{'associated_with': 1, 'attacks': 1, 'governs': 1, 'located_in': 7, 'member_of': 6, 'part_of': 1, 'part_of_group': 1, 'participates_in': 3, 'present_at': 2, 'same_as': 2}`
- Missing gold nodes: the fermentation cellar, Giant rats, flaming magma infused spider monstrosity, the rat cellar fight, the rat-clearing job, the shatter mage's tower mystery, the giant statue foot, the shatter mage's tower
- Extra candidate nodes: Stone Bridge, merchant guards party, residents of the shatter mages tower, 25 gold pieces reward, Broken alchemical tools, Enormous boulder, Excavation crew, Fermentation cellar, Flaming magma infused spider monstrosity, Foot of a once enormous statue, Giant rats, Glowkindle's Help Request, Health potions, Job Board, Magical crystals, The River's Edge Pub, Beautifully tiled hallway, Trapped mosaic, The Wizard's Tower Brewing Company, enormous boulder, Wizard's Tower Brewing Co, Unknown river name near Stone Bridge, Origin of Glowkindle's excavation disturbance, Hallway and mosaic traps in the brewery complex, Identity of the shatter mages tower resident, cat owl, flaming magma infused spider monstrosity, the troupe of gnomes, The River's Edge Pub
- Missing gold edges: the brewing company is located in the tower, the Stone Bridge spans the river at Stone Bridge, the cat owl is part of the rat cellar fight, the fermentation cellar is in the tower, the rat cellar fight threatens the excavation crew, the excavation crew works for the brewery, Glowkindle operates the Wizard's Tower Brewing Co, Glowkindle posted the rat-clearing job, the troupe of gnomes work at the brewery, Grishna knows where the brewery is located, Grishna operates The River's Edge Pub, the rat-clearing job was posted on the job board, the job board is in Stone Bridge, the heroes / party accept the rat-clearing job, the heroes / party travel to the brewery, giant rats are in the fermentation cellar, giant rats are part of the rat cellar fight

## mirathorn-city

Source: evals/graph_memory_layer/examples/mirathorn_city_world_doc/mirathorn_city_source.md

### `baseline`

- Nodes: 0; edges: 0; cost: $0.120289
- Node recall: 0.7143; edge recall: 0.1923
- Recognition: 0.857 (6/7); contamination: 0/4
- Party anchors inserted: []
- Party collective inserted: None
- Party membership edges: []
- Session context warnings: []
- Node kinds: `None`
- Edge predicates: `None`
- Missing gold nodes: the Copper and Quartz Inn, the Festival of Expansion, Float Goats, Grit and Grime, Luminox Sheep, the Nameless Goddess, the Wolf, Wizard's Tower Brewing Co
- Extra candidate nodes: Mirathorn Guard, Luminox Sheep, Tidal Turtles shells and mucus, Starling Cow milk, hides, and cheese, Sunflower Duck materials, Flutter Ferret wing scales and dust, Float Goat wool, milk, cheese, and buoyancy dust, Grand Market, Stormspire Academy, Lake Mirathorn Docks, The Broken Blade Inn, Temple of the Nameless Goddess, Festival of Expansion, Mirathorn city walls and gates, Out town tents and stalls, Toll system at the main gate, Protest signs and pamphlets, Mirathorn borders measured in Reaches, Aspitome, Lundayell Empire, Farmlands east of Mirathorn, Road to Mirathorn, Out town, Ancient city walls, Guard towers, Festival of Expansion, Grand Market, Lake Mirathorn Docks, The Broken Blade Inn, The Other Thing that consumed gods and other powers, Festival of Expansion as a pressured civic focal point, The Aspitome and the nameless goddess's sacrifice, The Elderwyld's edge-of-reality phenomenon, Founding after escape from the Lundayell Empire, Cult activity tied to sabotage, recruitment, and dark magic, Secret hideout holding non-human captives, Commander Thalia Ashenvale's magical manipulation, Corruption in the city guard, Shepherd's Flock protest at the city gate, Shepherd's Flock cultists, Agricultural Union, Commerce Representation, Craft Guilds, Infrastructure Representation, Undercity and Cultural Sectors
- Missing gold edges: node:barin-stonefoot operates node:copper-quartz-inn, node:wizards-tower-brewing-co located_near node:mirathorn, node:copper-quartz-inn located_in node:mirathorn, node:mirathorn-city-council governs node:mirathorn, node:festival-of-expansion commemorates node:nameless-goddess, node:shepherds-flock protests_at node:mirathorn, node:grit-and-grime located_in node:mirathorn, node:grobnok operates node:grit-and-grime, node:merril-tealeaf member_of node:mirathorn-city-council, node:mirathorn adjacent_to node:lake-mirathorn, node:mirathorn founded_by_settlers_from node:lundayell-empire, node:mirathorn located_in node:elderwyld, node:mirathorn located_near node:stormspire-peaks, node:mirathorn founded_using node:ancient-airship, node:rurik-stonehammer member_of node:mirathorn-city-council, node:temple-nameless-goddess murals_sourced_from node:lundayell-empire, node:temple-nameless-goddess dedicated_to node:nameless-goddess, node:thalia-ashenvale member_of node:mirathorn-city-council, node:tinkerbright member_of node:mirathorn-city-council, node:torrin-flamescale member_of node:mirathorn-city-council, node:the-wolf controls node:thalia-ashenvale

### `edge_and_node_packet`

- Nodes: 0; edges: 0; cost: $0.108935
- Node recall: 0.6786; edge recall: 0.1923
- Recognition: 0.857 (6/7); contamination: 0/4
- Party anchors inserted: []
- Party collective inserted: None
- Party membership edges: []
- Session context warnings: []
- Node kinds: `None`
- Edge predicates: `None`
- Missing gold nodes: the Copper and Quartz Inn, the Festival of Expansion, Float Goats, Grit and Grime, Luminox Sheep, the city council, the Nameless Goddess, the Wolf, Wizard's Tower Brewing Co
- Extra candidate nodes: Aspitome, Elderwylds, Luminox Sheep wool, Luminox Milk, Bioluminescent Dye, Tidal Turtle shell, Tidal Turtle mucus, Starling Cow milk, Starling Cow hide, Celestial Cheese, Sunflower Duck feathers, Sunflower Duck eggs, Sunflower Oil, Flutter Ferret wing scales, Flutter Ferret wing dust, Float Goat wool, Float Goat milk, Floating Cheese, Buoyancy Dust, Temple of the Nameless Goddess, The Great Hall, The Altar of Sacrifice, The Reflection Pool, The Sanctuary, Murals transported tile-by-tile from the Lundayell Empire, The Grand Market, Stormspire Academy, Lake Mirathorn Docks, The Broken Blade Inn, Ancient stone walls, Guard towers, Main gates of Mirathorn, Statues of the city's founders, Makeshift tents, stalls, and temporary shelters, Campfires and gathering spots, Pamphlets, Signs, Tolls to enter the city, The Great Hall, The Altar of Sacrifice, The Reflection Pool, The Sanctuary, Wizard's Tower Brewing Co., out town, Grand Market, Lake Mirathorn Docks, The Broken Blade Inn, Shepherd's Flock cultists, Origin of the Elderwyld and its edge-of-reality phenomenon, The lost gods, the Aspitome, and the Nameless Goddess sacrifice, Mirathorn’s founding by settlers fleeing the Lundayell Empire, Festival of Expansion as a civic ritual tied to the city’s origin, Corruption and illness linked to tainted goods in the market, Cult recruitment and disappearances tied to human supremacy preaching, Magical disturbances hinting at dark magic and natural disasters, Secret hideout holding non-human captives, Commander Thalia Ashenvale’s unexplained resistance to corruption accusations, Hidden passageways and tunnels used by the cult, Steep toll and protest at Mirathorn’s main gate, city guards, Stormspire Academy
- Missing gold edges: node:barin-stonefoot operates node:copper-quartz-inn, node:wizards-tower-brewing-co located_near node:mirathorn, node:copper-quartz-inn located_in node:mirathorn, node:mirathorn-city-council governs node:mirathorn, node:elara-swiftwind leads node:mirathorn-city-council, node:festival-of-expansion commemorates node:nameless-goddess, node:shepherds-flock protests_at node:mirathorn, node:grit-and-grime located_in node:mirathorn, node:grobnok operates node:grit-and-grime, node:merril-tealeaf member_of node:mirathorn-city-council, node:mirathorn adjacent_to node:lake-mirathorn, node:mirathorn founded_by_settlers_from node:lundayell-empire, node:mirathorn located_near node:stormspire-peaks, node:mirathorn founded_using node:ancient-airship, node:rurik-stonehammer member_of node:mirathorn-city-council, node:temple-nameless-goddess murals_sourced_from node:lundayell-empire, node:temple-nameless-goddess dedicated_to node:nameless-goddess, node:thalia-ashenvale member_of node:mirathorn-city-council, node:tinkerbright member_of node:mirathorn-city-council, node:torrin-flamescale member_of node:mirathorn-city-council, node:the-wolf controls node:thalia-ashenvale

