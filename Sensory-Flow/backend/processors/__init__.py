"""Assessment processors - route exercises to appropriate module"""

# Use fixed versions that match Colab implementations
from .one_leg_standing_fixed import process_one_leg_standing
from .tandem_walking_fixed import process_tandem_walking
from .jumping_jacks_fixed import process_jumping_jacks
from .prone_extension import process_prone_extension
from .supine_flexion import process_supine_flexion

__all__ = [
    "process_one_leg_standing",
    "process_tandem_walking", 
    "process_jumping_jacks",
    "process_prone_extension",
    "process_supine_flexion"
]
