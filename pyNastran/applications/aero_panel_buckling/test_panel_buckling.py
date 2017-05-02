import os
import unittest

from pyNastran.applications.aero_panel_buckling.run_buckling import run_panel_buckling
from pyNastran.utils.nastran_utils import run_nastran
from pyNastran.converters.nastran.nastranIOv import NastranIO
import pyNastran

pkg_path = pyNastran.__path__[0]
model_path = os.path.join(pkg_path, '..', 'models')


class TestPanelBuckling(unittest.TestCase):

    def test_panel_buckling_bwb(self):
        input_dir = os.path.join(model_path, 'bwb')
        bdf_filename = os.path.join(input_dir, 'bwb_saero.bdf')
        workpath = os.path.join(os.getcwd(), 'aero_buckling')

        op2_filename = os.path.join(workpath, 'bwb_saero.op2')
        #op2_filename = 'bwb_saero.op2'

        if workpath is not None:
            if not os.path.exists(workpath):
                os.makedirs(workpath)
                os.chdir(workpath)

        keywords = {
            'old' : 'no',
            'scr' : 'yes',
            'bat' : 'no',
            'news' : 'no',
        }
        if not os.path.exists(op2_filename) and 0:
            run_nastran(bdf_filename, keywords=keywords)
        if not os.path.exists(op2_filename):
            op2_filename = None

        run_panel_buckling(
            bdf_filename=bdf_filename,
            op2_filename=op2_filename,
            isubcase=1, workpath=workpath,
            build_model=False, rebuild_patches=True, write_buckling_bdfs=False,
            mode='displacement',
            parse_eigenvalues=False,

            run_nastran=False, nastran_keywords=keywords,
            overwrite_op2_if_exists=True,
            op2_filenames=None)

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
