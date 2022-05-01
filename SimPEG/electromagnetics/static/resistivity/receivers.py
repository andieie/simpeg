import numpy as np

# import properties
from ....utils import sdiag
from ....survey import BaseRx as BaseSimPEGRx


# Receiver classes
class BaseRx(BaseSimPEGRx):
    """
    Base DC/IP receiver class

    Parameters
    ----------
    locations : (n_loc, n_dim) np.ndarray
        Receiver locations. 
    orientation : str, default = ``None``
        Receiver orientation. Must be one of: ``None``, 'x', 'y' or 'z'
    data_type : str, default = 'volt'
        Data type. Choose one of: "volt", "apparent_resistivity", "apparent_chargeability"
    projField : str, default = 'phi'
        Fields solved on the mesh. Choose one of: "phi", "e", "j"
    """

    def __init__(self, locations=None, data_type='volt', orientation=None, projField="phi", **kwargs):
        super(BaseRx, self).__init__(locations=locations, **kwargs)

        self.orientation = orientation
        self.data_type = data_type
        self.projField = projField

    # orientation = properties.StringChoice(
    #     "orientation of the receiver. Must currently be 'x', 'y', 'z'", ["x", "y", "z"]
    # )

    @property
    def orientation(self):
        """Orientation of the receiver.

        Returns
        -------
        str
            Orientation of the receiver. One of {None, 'x', 'y', 'z'}
        """
        return self._orientation

    @orientation.setter
    def orientation(self, var):

        if var is not None:
            if isinstance(var, str):
                var = var.lower()
                if var not in ('x', 'y', 'z'):
                    raise ValueError(f"orientation must be either 'x', 'y' or 'z'. Got {var}")
            else:
                raise TypeError(f"orientation must be a str. Got {type(var)}")

        self._orientation = var

    # projField = properties.StringChoice(
    #     "field to be projected in the calculation of the data",
    #     choices=["phi", "e", "j"],
    #     default="phi",
    # )

    _geometric_factor = {}


    # @property
    # def projField(self):
    #     """Field Type projection (e.g. e b ...)"""
    #     return self.knownRxTypes[self.rxType][0]

    @property
    def projField(self):
        """Fields on the mesh

        Returns
        -------
        str
            Fields defined on mesh. One of {"phi", "e", "j"}
        """
        return self._projField

    @projField.setter
    def projField(self, var):

        if isinstance(var, str):
            var = var.lower()
            if var not in ('phi', 'e', 'j'):
                raise ValueError(f"projField must be either 'phi', 'e', 'j'. Got {var}")
        else:
            raise TypeError(f"projField must be a str. Got {type(var)}")

        self._projField = var


    # data_type = properties.StringChoice(
    #     "Type of DC-IP survey",
    #     required=True,
    #     default="volt",
    #     choices=["volt", "apparent_resistivity", "apparent_chargeability"],
    # )

    @property
    def data_type(self):
        """Data type; i.e. "volt", "apparent_resistivity", "apparent_chargeability"

        Returns
        -------
        str
            Data type; i.e. "volt", "apparent_resistivity", "apparent_chargeability"
        """
        return self._data_type

    @data_type.setter
    def data_type(self, var):

        if isinstance(var, str):
            if var.lower() in ("potential", "potentials", "volt", "v", "voltages", "voltage"):
                self._data_type = 'volt'
            elif var.lower() in ("apparent resistivity","appresistivity","apparentresistivity","apparent-resistivity","apparent_resistivity","appres"):
                self._data_type = 'apparent_resistivity'
            elif var.lower() in ("apparent chargeability","appchargeability","apparentchargeability","apparent-chargeability","apparent_chargeability"):
                self._data_type = 'apparent_chargeability'
            else:
                raise ValueError(f"data_type must be either 'volt', 'apparent_resistivity' or 'apparent_chargeability'. Got {var}")
        else:
            raise TypeError(f"data_type must be a str. Got {type(var)}")

    # data_type = 'volt'

    # knownRxTypes = {
    #     'phi': ['phi', None],
    #     'ex': ['e', 'x'],
    #     'ey': ['e', 'y'],
    #     'ez': ['e', 'z'],
    #     'jx': ['j', 'x'],
    #     'jy': ['j', 'y'],
    #     'jz': ['j', 'z'],
    # }

    @property
    def geometric_factor(self):
        r"""
        Calculate geometric factor for every receiver.

        Consider you have current electrodes *A* and *B*, and potential electrodes *M* and *N*.
        Let :math:`R_{AM}` represents the scalar horizontal distance between electrodes *A*
        and *M*; likewise for :math:`R_{BM}`, :math:`R_{AN}` and :math:`R_{BN}`.
        The geometric factor is given by:

        .. math::
            G = \frac{1}{C} \bigg [ \frac{1}{R_{AM}} - \frac{1}{R_{BM}} - \frac{1}{R_{AN}} + \frac{1}{R_{BN}}  \bigg ]

        where :math:`C=2\pi` for a halfspace and :math:`C=4\pi` for a wholespace.

        Returns
        -------
        (nD) numpy.ndarray
            Geometric factor for each datum

        """
        return self._geometric_factor

    # def projected_grid(self, f):
    #     """Grid Location projection (e.g. Ex Fy ...)"""
    #     # field = self.knownRxTypes[self.rxType][0]
    #     # orientation = self.knownRxTypes[self.rxType][1]
    #     if self.orientation is not None:
    #         return f._GLoc(self.projField) + self.orientation
    #     return f._GLoc(self.projField)

    def eval(self, src, mesh, f):
        """Project fields from the mesh to the receiver(s).

        Parameters
        ----------
        src : SimPEG.electromagnetics.static.resistivity.sources.BaseSrc
            A DC/IP source
        mesh : discretize.base.BaseMesh
            The mesh on which the discrete set of equations is solved
        f : SimPEG.electromagnetic.static.fields.FieldsDC
            The solution for the fields defined on the mesh
        
        Returns
        -------
        np.ndarray
            Fields projected to the receiver(s)
        """
        if self.orientation is not None:
            projected_grid = f._GLoc(self.projField) + self.orientation
        else:
            projected_grid = f._GLoc(self.projField)

        P = self.getP(mesh, projected_grid)
        proj_f = self.projField
        if proj_f == "phi":
            proj_f = "phiSolution"
        v = P * f[src, proj_f]

        if self.data_type == "apparent_resistivity":
            try:
                if mesh.dim == 2:
                    return v / self.geometric_factor[src][:, None]
                return v / self.geometric_factor[src]
            except KeyError:
                raise KeyError(
                    "Receiver geometric factor has not been set, please execute "
                    "survey.set_geometric_factor()"
                )
        return v

    def evalDeriv(self, src, mesh, f, v=None, adjoint=False):
        """Derivative of the projected fields with respect to the model, times a vector.

        Parameters
        ----------
        src : SimPEG.electromagnetics.static.resistivity.sources.BaseSrc
            A frequency-domain EM source
        mesh : discretize.base.BaseMesh
            The mesh on which the discrete set of equations is solved
        f : SimPEG.electromagnetic.static.resistivity.fields.FieldsDC
            The solution for the fields defined on the mesh
        du_dm_v : np.ndarray, default = ``None``
            The derivative of the fields on the mesh with respect to the model,
            times a vector.
        v : np.ndarray
            The vector which being multiplied
        adjoint : bool, default = ``False``
            If ``True``, return the ajoint
        
        Returns
        -------
        np.ndarray
            The derivative times a vector at the receiver(s)
        """
        if self.orientation is not None:
            projected_grid = f._GLoc(self.projField) + self.orientation
        else:
            projected_grid = f._GLoc(self.projField)

        P = self.getP(mesh, projected_grid)

        factor = None
        if self.data_type == "apparent_resistivity":
            factor = 1.0 / self.geometric_factor[src]

        if v is None:
            if factor is not None:
                P = sdiag(factor) @ P
            if adjoint:
                return P.T
            return P

        if not adjoint:
            v = P @ v
            if factor is not None:
                v = factor * v
            return v
        elif adjoint:
            if factor is not None:
                v = factor * v
            return P.T @ v


class Dipole(BaseRx):
    """
    Dipole receiver class

    Parameters
    ----------
    locations_m : (n_loc, dim) numpy.ndarray
        M electrode locations; remember to set 'locations_n' keyword argument to define N electrode locations.
    locations_n : (n_loc, dim) numpy.ndarray
        N electrode locations; remember to set 'locations_m' keyword argument to define M electrode locations.
    locations : list or tuple of length 2 of np.ndarray
        M and N electrode locations. In this case, do not set the 'locations_m' and 'locations_n'
        keyword arguments. And we supply a list or tuple of the form [locations_m, locations_n].
    orientation : str, default = ``None``
        Receiver orientation. Must be one of: ``None``, 'x', 'y' or 'z'
    data_type : str, default = 'volt'
        Data type. Choose one of: "volt", "apparent_resistivity", "apparent_chargeability"
    """

    # Threshold to be assumed as a pole receiver
    threshold = 1e-5

    # locations = properties.List(
    #     "list of locations of each electrode in a dipole receiver",
    #     RxLocationArray("location of electrode", shape=("*", "*")),
    #     min_length=1,
    #     max_length=2,
    # )

    def __init__(self, locations_m=None, locations_n=None, locations=None, **kwargs):
        # if locations_m set, then use locations_m, locations_n
        if locations_m is not None or locations_n is not None:
            if locations_n is None or locations_m is None:
                raise ValueError(
                    "For a dipole receiver both locations_m and locations_n "
                    "must be set"
                )

            if locations is not None:
                raise ValueError(
                    "Cannot set both locations and locations_m, locations_n. "
                    "Please provide either locations=(locations_m, locations_n) "
                    "or both locations_m=locations_m, locations_n=locations_n"
                )

            locations = [np.atleast_2d(locations_m), np.atleast_2d(locations_n)]

        if locations is None:
            raise AttributeError(
                "Receiver cannot be instantiated without assigning 'locations'."
                "Please provide either locations=(locations_m, locations_n) "
                "or both locations_m=locations_m, locations_n=locations_n"
            )

        # instantiate
        super(Dipole, self).__init__(locations=locations, **kwargs)

    def __repr__(self):
        return ",\n".join(
            [
                f"{self.__class__.__name__}(m: {m}; n: {n})"
                for (m, n) in zip(self.locations_m, self.locations_n)
            ]
        )

    @property
    def locations(self):
        """M and N electrode locations

        Returns
        -------
        list of 2 (n_loc, dim) np.ndarray
            M and N electrode locations.
        """
        return self._locations

    @locations.setter
    def locations(self, locs):
        if len(locs) != 2:
            raise ValueError(
                    "locations must be a list or tuple of length 2: "
                    "[locations_m, locations_n]. The input locations has "
                    f"length {len(locs)}"
                )
        
        locs = [np.atleast_2d(locs[0]), np.atleast_2d(locs[1])]

        # check the size of locations_m, locations_n
        if locs[0].shape != locs[1].shape:
            raise ValueError(
                f"locations_m (shape: {locs[0].shape}) and "
                f"locations_n (shape: {locs[1].shape}) need to be "
                f"the same size"
            )
            
        self._locations = locs

    @property
    def locations_m(self):
        """Locations of the M-electrodes

        Returns
        -------
        (n, dim) numpy.ndarray
            Locations of the M-electrodes
        """
        return self.locations[0]

    @property
    def locations_n(self):
        """Locations of the N-electrodes

        Returns
        -------
        (n, dim) numpy.ndarray
            Locations of the N-electrodes
        """
        return self.locations[1]

    @property
    def nD(self):
        """Number of data associate with the receiver(s).

        Returns
        -------
        int
            Number of data associated with the receiver(s).
        """
        return self.locations[0].shape[0]

    def getP(self, mesh, projected_grid, transpose=False):
        """
        Get projection matrix from mesh to receivers

        Parameters
        ----------
        mesh : discretize.base.BaseMesh
            The mesh on which the discrete set of equations is solved
        projected_grid : str
            Tensor locations on the mesh being interpolated from. *projected_grid* must be one of:

            - 'Ex', 'edges_x'           -> x-component of field defined on x edges
            - 'Ey', 'edges_y'           -> y-component of field defined on y edges
            - 'Ez', 'edges_z'           -> z-component of field defined on z edges
            - 'Fx', 'faces_x'           -> x-component of field defined on x faces
            - 'Fy', 'faces_y'           -> y-component of field defined on y faces
            - 'Fz', 'faces_z'           -> z-component of field defined on z faces
            - 'N', 'nodes'              -> scalar field defined on nodes
            - 'CC', 'cell_centers'      -> scalar field defined on cell centers
            - 'CCVx', 'cell_centers_x'  -> x-component of vector field defined on cell centers
            - 'CCVy', 'cell_centers_y'  -> y-component of vector field defined on cell centers
            - 'CCVz', 'cell_centers_z'  -> z-component of vector field defined on cell centers

        transpose : bool, default = ``False``
            Return the transpose of the projection matrix

        Returns
        -------
        scipy.sparse.csr_matrix
            P, the interpolation matrix

        """
        if mesh in self._Ps:
            return self._Ps[mesh]

        P0 = mesh.get_interpolation_matrix(self.locations[0], projected_grid)
        P1 = mesh.get_interpolation_matrix(self.locations[1], projected_grid)
        P = P0 - P1

        if self.storeProjections:
            self._Ps[mesh] = P

        if transpose:
            P = P.toarray().T

        return P


class Pole(BaseRx):
    """
    Pole receiver class

    Parameters
    ----------
    locations : (n_loc, dim) np.ndarray
        Receiver locations. 
    orientation : str, default = ``None``
        Receiver orientation. Must be one of: ``None``, 'x', 'y' or 'z'
    data_type : str, default = 'volt'
        Data type. Choose one of: "volt", "apparent_resistivity", "apparent_chargeability"
    """

    # def __init__(self, locationsM, **kwargs):

    #     locations = np.atleast_2d(locationsM)
    #     # We may not need this ...
    #     BaseRx.__init__(self, locations)

    def __repr__(self):
        return ",\n".join(
            [f"{self.__class__.__name__}(m: {m})" for m in self.locations]
        )

    @property
    def nD(self):
        """Number of data associate with the receiver(s).

        Returns
        -------
        int
            Number of data associated with the receiver(s).
        """
        return self.locations.shape[0]

    def getP(self, mesh, projected_grid):
        """
        Get projection matrix from mesh to receivers

        Parameters
        ----------
        mesh : discretize.base.BaseMesh
            The mesh on which the discrete set of equations is solved
        projected_grid : str
            Tensor locations on the mesh being interpolated from. *projected_grid* must be one of:

            - 'Ex', 'edges_x'           -> x-component of field defined on x edges
            - 'Ey', 'edges_y'           -> y-component of field defined on y edges
            - 'Ez', 'edges_z'           -> z-component of field defined on z edges
            - 'Fx', 'faces_x'           -> x-component of field defined on x faces
            - 'Fy', 'faces_y'           -> y-component of field defined on y faces
            - 'Fz', 'faces_z'           -> z-component of field defined on z faces
            - 'N', 'nodes'              -> scalar field defined on nodes
            - 'CC', 'cell_centers'      -> scalar field defined on cell centers
            - 'CCVx', 'cell_centers_x'  -> x-component of vector field defined on cell centers
            - 'CCVy', 'cell_centers_y'  -> y-component of vector field defined on cell centers
            - 'CCVz', 'cell_centers_z'  -> z-component of vector field defined on cell centers

        Returns
        -------
        scipy.sparse.csr_matrix
            P, the interpolation matrix

        """
        if mesh in self._Ps:
            return self._Ps[mesh]

        P = mesh.get_interpolation_matrix(self.locations, projected_grid)

        if self.storeProjections:
            self._Ps[mesh] = P

        return P
