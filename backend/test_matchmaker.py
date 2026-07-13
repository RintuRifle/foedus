
import asyncio
from app.agents.agent_1_matchmaker import matchmaker_node
async def run():
    print('Starting')
    state = {'tender_text': 'test', 'company_profile': {}, 'tender_metadata': {}}
    res = await matchmaker_node(state)
    print(res)

asyncio.run(run())

