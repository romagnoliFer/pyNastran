from __future__ import annotations
#from itertools import count
from typing import TYPE_CHECKING
import numpy as np

#from pyNastran.utils.numpy_utils import integer_types
from pyNastran.bdf.field_writer_8 import print_card_8 # , print_float_8, print_field_8
#from pyNastran.bdf.field_writer_16 import print_card_16, print_scientific_16, print_field_16
#from pyNastran.bdf.field_writer_double import print_scientific_double
from pyNastran.bdf.bdf_interface.assign_type import (
    integer, double, integer_or_blank, double_or_blank)
#from pyNastran.bdf.cards.elements.bars import set_blank_if_default

from pyNastran.dev.bdf_vectorized3.cards.base_card import Element, Property
from pyNastran.dev.bdf_vectorized3.cards.write_utils import array_str, array_default_int
from pyNastran.dev.bdf_vectorized3.bdf_interface.geom_check import geom_check
from pyNastran.dev.bdf_vectorized3.utils import hstack_msg
from .utils import get_mass_from_property
if TYPE_CHECKING:
    from pyNastran.bdf.bdf_interface.bdf_card import BDFCard


class CMASS1(Element):

    def add_card(self, card: BDFCard, comment: str=''):
        """
        Adds a CMASS1 card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        eid = integer(card, 1, 'eid')
        pid = integer_or_blank(card, 2, 'pid', default=eid)
        n1 = integer(card, 3, 'g1')
        c1 = integer_or_blank(card, 4, 'c1', default=0)
        n2 = integer_or_blank(card, 5, 'g2', default=0)
        c2 = integer_or_blank(card, 6, 'c2', default=0)
        assert len(card) <= 7, f'len(CMASS1 card) = {len(card):d}\ncard={card}'
        self.cards.append((eid, pid, [n1, n2], [c1, c2], comment))
        self.n += 1

    def parse_cards(self):
        if self.n == 0:
            return
        ncards = len(self.cards)
        if ncards == 0:
            return
        element_id = np.zeros(ncards, dtype='int32')
        property_id = np.zeros(ncards, dtype='int32')
        nodes = np.zeros((ncards, 2), dtype='int32')
        components = np.zeros((ncards, 2), dtype='int32')

        for icard, card in enumerate(self.cards):
            (eidi, pidi, nidsi, componentsi, comment) = card
            element_id[icard] = eidi
            property_id[icard] = pidi
            nodes[icard, :] = nidsi
            components[icard, :] = componentsi
        self._save(element_id, property_id, nodes, components)
        self.cards = []

    def _save(self,
              element_id: np.ndarray,
              property_id: np.ndarray,
              nodes: np.ndarray, components: np.ndarray) -> None:
        assert len(self.element_id) == 0
        self.element_id = element_id
        self.property_id = property_id
        self.nodes = nodes
        self.components = components

    def __apply_slice__(self, elem: CMASS2, i: np.ndarray) -> None:
        elem.element_id = self.element_id[i]
        elem.property_id = self.property_id[i]
        elem.nodes = self.nodes[i, :]
        elem.components = self.components[i, :]
        elem.n = len(i)

    def write(self, size: int=8) -> str:
        if len(self.element_id) == 0:
            return ''
        if size == 8:
            print_card = print_card_8

        lines = []
        element_id = array_str(self.element_id, size=size)
        property_id = array_str(self.property_id, size=size)
        nodes_ = array_default_int(self.nodes, default=0, size=size)
        components_ = array_default_int(self.components, default=0, size=size)
        for eid, pid, (n1, n2), (c1, c2) in zip(element_id, property_id, nodes_, components_):
            list_fields = ['CMASS1', eid, pid, n1, c1, n2, c2]
            lines.append(print_card(list_fields))
        return ''.join(lines)

    @property
    def allowed_properties(self):
        return [prop for prop in [self.model.pmass]
                if prop.n > 0]

    def mass(self):
        mass = get_mass_from_property(self.property_id, self.allowed_properties)
        return mass
    #def length(self) -> np.ndarray:
        #length = line_length(self.model, self.nodes)
        #return length

    def geom_check(self, missing: dict[str, np.ndarray]):
        nid = self.model.grid.node_id
        pids = hstack_msg([prop.property_id for prop in self.allowed_properties],
                          msg=f'no pmass properties for {self.type}')
        pids.sort()
        geom_check(self,
                   missing,
                   node=(nid, self.nodes),
                   property_id=(pids, self.property_id))
        s = 1

    def centroid(self) -> np.ndarray:
        #ispoint = np.where(self.components.ravel() == 0)[0]
        #igrid = ~ispoint
        #nodes = self.nodes.ravel()[igrid]
        #nodes = nodes.reshape(len(nodes), 1)
        centroid = point_centroid(self.model, self.nodes)
        return centroid

    def center_of_mass(self) -> np.ndarray:
        return self.centroid()


def point_centroid(model, nodes: np.ndarray) -> np.ndarray:
    #unids = np.unique(nodes.ravel())
    grid = model.grid # .slice_card_by_node_id(unids)

    xyz = grid.xyz_cid0()
    nid = grid.node_id
    nelement, nnodes = nodes.shape
    node_count = np.zeros(nelement, dtype='int32')
    centroid = np.zeros((nelement, 3), dtype='float64')
    inode = np.searchsorted(nid, nodes)
    exists = (nid[inode] == nodes)
    for i in range(nnodes):
        exist = exists[:, i]
        inodei = inode[exist, i]
        centroid[exist, :] = xyz[inodei, :]
        node_count[exist] += 1
    centroid /= node_count[:, np.newaxis]
    assert centroid.shape[0] == nodes.shape[0]
    return centroid


class CMASS2(Element):
    """
    Defines a scalar mass element without reference to a property entry.

    +--------+-----+-----+----+----+----+----+
    |    1   |  2  |  3  |  4 |  5 |  6 |  7 |
    +========+=====+=====+====+====+====+====+
    | CMASS2 | EID |  M  | G1 | C1 | G2 | C2 |
    +--------+-----+-----+----+----+----+----+

    """
    def add_card(self, card: BDFCard, comment: str='') -> int:
        eid = integer(card, 1, 'eid')
        mass = double_or_blank(card, 2, 'mass', default=0.)
        n1 = integer_or_blank(card, 3, 'g1', default=0)
        c1 = integer_or_blank(card, 4, 'c1', default=0)
        n2 = integer_or_blank(card, 5, 'g2', default=0)
        c2 = integer_or_blank(card, 6, 'c2', default=0)
        assert len(card) <= 7, f'len(CMASS2 card) = {len(card):d}\ncard={card}'
        self.cards.append((eid, mass, [n1, n2], [c1, c2], comment))
        self.n += 1
        return self.n

    def parse_cards(self):
        if self.n == 0:
            return
        ncards = len(self.cards)
        if ncards == 0:
            return
        element_id = np.zeros(ncards, dtype='int32')
        mass = np.zeros(ncards, dtype='float64')
        nodes = np.zeros((ncards, 2), dtype='int32')
        components = np.zeros((ncards, 2), dtype='int32')

        for icard, card in enumerate(self.cards):
            (eidi, massi, nidsi, componentsi, comment) = card
            element_id[icard] = eidi
            mass[icard] = massi
            nodes[icard, :] = nidsi
            components[icard, :] = componentsi
        self._save(element_id, mass, nodes, components)
        self.cards = []

    def _save(self, element_id: np.ndarray,
              mass: np.ndarray,
              nodes: np.ndarray, components: np.ndarray) -> None:
        assert len(self.element_id) == 0
        self.element_id = element_id
        self._mass = mass
        self.nodes = nodes
        self.components = components

    def __apply_slice__(self, elem: CMASS2, i: np.ndarray) -> None:
        elem.element_id = self.element_id[i]
        elem._mass = self._mass[i]
        elem.nodes = self.nodes[i, :]
        elem.components = self.components[i, :]
        elem.n = len(i)

    def write(self, size: int=8) -> str:
        if len(self.element_id) == 0:
            return ''
        if size == 8:
            print_card = print_card_8

        lines = []
        element_id = array_str(self.element_id, size=size)
        nodes_ = array_default_int(self.nodes, default=0, size=size)
        components_ = array_default_int(self.components, default=0, size=size)
        for eid, mass, (n1, n2), (c1, c2) in zip(element_id, self._mass,
                                                nodes_, components_):
            list_fields = ['CMASS2', eid, mass, n1, c1, n2, c2]
            lines.append(print_card(list_fields))
        return ''.join(lines)

    def mass(self) -> np.ndarray:
        return self._mass

    def centroid(self) -> np.ndarray:
        centroid = point_centroid(self.model, self.nodes)
        return centroid

    def center_of_mass(self) -> np.ndarray:
        return self.centroid()


class CMASS3(Element):

    def add_card(self, card: BDFCard, comment: str=''):
        """
        Adds a CMASS3 card from ``BDF.add_card(...)``

        Parameters
        ----------
        card : BDFCard()
            a BDFCard object
        comment : str; default=''
            a comment for the card

        """
        eid = integer(card, 1, 'eid')
        pid = integer_or_blank(card, 2, 'pid', default=eid)
        s1 = integer_or_blank(card, 3, 's1', default=0)
        s2 = integer_or_blank(card, 4, 's2', default=0)
        assert len(card) <= 5, f'len(CMASS3 card) = {len(card):d}\ncard={card}'
        self.cards.append((eid, pid, s1, s2, comment))
        self.n += 1

    def parse_cards(self):
        if self.n == 0:
            return
        ncards = len(self.cards)
        if ncards == 0:
            return
        element_id = np.zeros(ncards, dtype='int32')
        property_id = np.zeros(ncards, dtype='int32')
        spoints = np.zeros((ncards, 2), dtype='int32')

        for icard, card in enumerate(self.cards):
            (eid, pid, s1, s2, comment) = card
            element_id[icard] = eid
            property_id[icard] = pid
            spoints[icard, :] = [s1, s2]
        self._save(element_id, property_id, spoints)
        self.cards = []

    def _save(self, element_id: np.ndarray,
              property_id: np.ndarray,
              spoints: np.ndarray) -> None:
        assert len(self.element_id) == 0
        assert element_id.min() > 0, element_id
        assert spoints.min() >= 0, spoints
        self.element_id = element_id
        self.property_id = property_id
        self.spoints = spoints
        self.n = len(element_id)

    def write(self, size: int=8) -> str:
        if len(self.element_id) == 0:
            return ''
        #if size == 8:
            #print_card = print_card_8

        lines = []
        element_id = array_str(self.element_id, size=size)
        property_id = array_str(self.property_id, size=size)
        spoints_ = array_default_int(self.spoints, default=0, size=size)
        for eid, pid, (spoint1, spoint2) in zip(element_id, property_id, spoints_):
            msg = 'CMASS3  %8s%8s%8s%8s\n' % (eid, pid, spoint1, spoint2)
            lines.append(msg)
        return ''.join(lines)

    @property
    def allowed_properties(self):
        return [prop for prop in [self.model.pmass]
                if prop.n > 0]


class CMASS4(Element):
    """
    Defines a scalar mass element that is connected only to scalar points,
    without reference to a property entry

    +--------+-----+-----+----+----+
    |    1   |  2  |  3  |  4 |  5 |
    +========+=====+=====+====+====+
    | CMASS4 | EID |  M  | S1 | S2 |
    +--------+-----+-----+----+----+

    """
    def add_card(self, card: BDFCard, comment: str=''):
        eid = integer(card, 1, 'eid')
        mass = double(card, 2, 'mass')
        s1 = integer_or_blank(card, 3, 's1', default=0)
        s2 = integer_or_blank(card, 4, 's2', default=0)
        self.cards.append((eid, mass, s1, s2, comment))
        self.n += 1
        if card.field(5):
            eid = integer(card, 5, 'eid')
            mass = double(card, 6, 'mass')
            s1 = integer_or_blank(card, 7, 's1', default=0)
            s2 = integer_or_blank(card, 8, 's2', default=0)
            self.cards.append((eid, mass, s1, s2, comment))
            self.n += 1
        assert len(card) <= 9, f'len(CMASS4 card) = {len(card):d}\ncard={card}'

    def parse_cards(self):
        if self.n == 0:
            return
        ncards = len(self.cards)
        if ncards == 0:
            return
        element_id = np.zeros(ncards, dtype='int32')
        mass = np.zeros(ncards, dtype='float64')
        spoints = np.zeros((ncards, 2), dtype='int32')

        for icard, card in enumerate(self.cards):
            (eid, massi, s1, s2, comment) = card
            element_id[icard] = eid
            mass[icard] = massi
            spoints[icard, :] = [s1, s2]
        self._save(element_id, mass, spoints)
        self.cards = []

    def _save(self, element_id, mass, spoints):
        assert len(self.element_id) == 0
        assert element_id.min() > 0, element_id
        assert spoints.min() >= 0, spoints
        self.element_id = element_id
        self._mass = mass
        self.spoints = spoints
        self.n = len(element_id)

    def write(self, size: int=8) -> str:
        if len(self.element_id) == 0:
            return ''
        if size == 8:
            print_card = print_card_8

        lines = []
        element_id = array_str(self.element_id, size=size)
        spoints_ = array_default_int(self.spoints, default=0, size=size)
        for eid, massi, spoints in zip(element_id, self._mass, spoints_):
            list_fields = ['CMASS4', eid, massi, spoints[0], spoints[1]]
            lines.append(print_card(list_fields))
        return ''.join(lines)


class PMASS(Property):
    """
    Scalar Mass Property
    Specifies the mass value of a scalar mass element (CMASS1 or CMASS3 entries).

    +-------+------+------+------+------+------+----+------+----+
    |   1   |   2  |   3  |   4  |   5  |   6  |  7 |   8  |  9 |
    +=======+======+======+======+======+======+====+======+====+
    | PMASS | PID1 |  M1  | PID2 |  M2  | PID3 | M3 | PID4 | M4 |
    +-------+------+------+------+------+------+----+------+----+
    | PMASS |   7  | 4.29 |   6  | 13.2 |      |    |      |    |
    +-------+------+------+------+------+------+----+------+----+
    """
    def add_card(self, card: BDFCard, comment: str='') -> None:
        for icard, j in enumerate([1, 3, 5, 7]):
            if card.field(j):
                ioffset = icard * 2
                pid = integer(card, 1 + ioffset, 'pid')
                mass = double_or_blank(card, 2 + ioffset, 'mass', default=0.)
                self.cards.append((pid, mass, comment))
                comment = ''
                self.n += 1
        assert len(card) <= 9, f'len(PMASS card) = {len(card):d}\ncard={card}'

    def parse_cards(self):
        if self.n == 0:
            return
        ncards = len(self.cards)
        if ncards == 0:
            return

        property_id = np.zeros(ncards, dtype='int32')
        mass = np.zeros(ncards, dtype='float64')
        for icard, card in enumerate(self.cards):
            (pid, massi, comment) = card
            property_id[icard] = pid
            mass[icard] = massi
        self._save(property_id, mass)
        self.cards = []

    def _save(self, property_id: np.ndarray, mass: np.ndarray) -> None:
        assert len(self.property_id) == 0
        self.property_id = property_id
        self._mass = mass
        self.n = len(property_id)

    def write(self, size: int=8) -> str:
        if len(self.property_id) == 0:
            return ''
        lines = []
        if size == 8:
            print_card = print_card_8

        property_id = array_str(self.property_id, size=size)
        for pid, mass in zip(property_id, self._mass):
            list_fields = ['PMASS', pid, mass]
            lines.append(print_card(list_fields))
        return ''.join(lines)

    def mass(self) -> np.ndarray:
        return self._mass