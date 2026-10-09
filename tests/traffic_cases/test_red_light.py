"""Mechanism-only test network. Never used as the delivered geographic network."""
import subprocess
from pathlib import Path
import pytest


def test_red_light_holds_single_vehicle_then_releases(tmp_path):
    import libsumo as sim,sumolib,sys
    binary=Path(sys.executable).parent/'netgenerate'
    if not binary.exists():pytest.skip('SUMO netgenerate not installed')
    netfile=tmp_path/'mechanism.net.xml'
    subprocess.run([str(binary),'--grid','--grid.x-number','3','--grid.y-number','2','--grid.length','100','--tls.guess','--tls.guess.threshold','0','-o',str(netfile)],check=True,capture_output=True)
    net=sumolib.net.readNet(str(netfile));tls_ids=[t.getID() for t in net.getTrafficLights()]
    assert tls_ids
    tls_id=tls_ids[0];node=net.getNode(tls_id)
    incoming=next(e for e in node.getIncoming() if e.allows('passenger'))
    outgoing=next(e for e in node.getOutgoing() if e.getToNode()!=incoming.getFromNode() and e.allows('passenger'))
    types=tmp_path/'routes.xml';types.write_text('<routes><vType id="car" vClass="passenger"/></routes>')
    sim.start(['sumo','-n',str(netfile),'-r',str(types),'--step-length','.5','--time-to-teleport','-1','--no-step-log','true'])
    try:
        links=sim.trafficlight.getControlledLinks(tls_id)
        green_state=sim.trafficlight.getRedYellowGreenState(tls_id)
        sim.trafficlight.setRedYellowGreenState(tls_id,'r'*len(green_state))
        sim.route.add('r',[incoming.getID(),outgoing.getID()]);sim.vehicle.add('v','r',typeID='car',depart='0')
        for _ in range(60):sim.simulationStep()
        assert 'v' in sim.vehicle.getIDList()
        assert sim.vehicle.getRoadID('v')==incoming.getID()
        assert sim.vehicle.getSpeed('v')<.1
        assert sim.vehicle.getLanePosition('v')<sim.lane.getLength(sim.vehicle.getLaneID('v'))
        # Empty network, one vehicle: release its legal pre-existing movement for the isolated test.
        sim.trafficlight.setRedYellowGreenState(tls_id,'G'*len(green_state))
        arrived=False
        for _ in range(100):
            sim.simulationStep();arrived=arrived or 'v' in sim.simulation.getArrivedIDList()
        assert arrived and sim.simulation.getStartingTeleportNumber()==0
    finally:sim.close()
