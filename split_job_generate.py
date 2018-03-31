import shutil
import numpy as np
import fileinput

num_splits = 10
nodes = 16
wallhour = 7
cdf_dist = np.linspace(0,1, num_splits+1)

def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copy(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

def gen_input(run_num, cdf_begin, cdf_end):
    input_file = """
<Simulation verbosity="all">
  <RunInfo>
    <WorkingDir>.</WorkingDir>
    <!-- ordered list of step names that RAVEN will run -->
    <Sequence>%s,outputResults</Sequence>
    <!-- number of parallel runs executed simultaneously -->
    <batchSize>10</batchSize>
    <!--
    <JobName>raven-serpent</JobName>
    <NumMPI>1</NumMPI>
    <mode>mpi<runQSUB/></mode>
    <expectedTime>48:00:00</expectedTime>-->
  </RunInfo>

  <Files>
    <Input name="originalInput" type="">msbr_input_comp.serpent</Input>
  </Files>


 <VariableGroups>
    <ExternalXML node='Group'
                 xmlToLoad='../aux-input-files/feature_isotopes.xml'/>    

    <ExternalXML node='Group'
                 xmlToLoad='../aux-input-files/target_isotopes_keff.xml'/>

  </VariableGroups>

  <Models>
    <Code name="SERPENT" subType="Serpent">
      <executable>/projects/sciteam/bahg/serpent/src/sss2 -omp 32 </executable>
      <clargs arg="aprun -n 9 -d 32 " type="prepend"/>
      <clargs arg="" extension=".serpent" type="input"/>
    </Code>
  </Models>

  <Distributions>
    <!-- uniform distribution from 0.1 to 1 -->
    <Uniform name="u233_mole_frac">
      <lowerBound>0.2</lowerBound>
      <upperBound>0.3</upperBound>
    </Uniform>
  </Distributions>

  <Functions>
    <External name='li7_mass_frac' file='calc_li7'>
      <variable>u233_mole_frac</variable>
    </External>

    <External name='li6_mass_frac' file='calc_li6'>
      <variable>u233_mole_frac</variable>
    </External>

    <External name='f19_mass_frac' file='calc_f19'>
      <variable>u233_mole_frac</variable>
    </External>

    <External name='be9_mass_frac' file='calc_be9'>
      <variable>u233_mole_frac</variable>
    </External>

    <External name='th232_mass_frac' file='calc_th232'>
      <variable>u233_mole_frac</variable>
    </External>
    
    <External name='u233_mass_frac' file='calc_u233'>
      <variable>u233_mole_frac</variable>
    </External>
  </Functions>

  <Samplers>
    <Grid name="myGrid">
      <variable name="u233_mole_frac">
        <distribution>u233_mole_frac</distribution>
        <!-- equally spaced steps with lower and upper bound -->
        <grid construction="equal" steps="30" type="CDF">%s %s</grid>
      </variable>

      <variable name="li7_mass_frac">
        <function>li7_mass_frac</function>
      </variable>

      <variable name="li6_mass_frac">
        <function>li6_mass_frac</function>
      </variable>

      <variable name="f19_mass_frac">
        <function>f19_mass_frac</function>
      </variable>

      <variable name="be9_mass_frac">
        <function>be9_mass_frac</function>
      </variable>

      <variable name="th232_mass_frac">
        <function>th232_mass_frac</function>
      </variable>

      <variable name="u233_mass_frac">
        <function>u233_mass_frac</function>
      </variable>

    </Grid>
  </Samplers>

  <Steps>
    <MultiRun name="%s">
      <!-- runGrid runs serpent by the number of steps with sampled variable -->
      <Input   class="Files"       type=""          >originalInput</Input>
      <Model   class="Models"      type="Code"      >SERPENT</Model>
      <Sampler class="Samplers"    type="Grid"      >myGrid</Sampler>
      <Output  class="DataObjects" type="PointSet"  >outPointSet</Output>
    </MultiRun>
    <IOStep name="outputResults">
      <Input  class="DataObjects" type="PointSet"   >outPointSet</Input>
      <Output  class="OutStreams"  type="Print"     >outPointSet_dump%s</Output>
    </IOStep>
  </Steps>

  <OutStreams>
    <Print name="outPointSet_dump%s">
      <type>csv</type>
      <source>outPointSet</source>
    </Print>
  </OutStreams>

  <DataObjects>
    <PointSet name="outPointSet">
      <Input>feature_space</Input>
      <Output>target_space</Output>
    </PointSet>

  </DataObjects>

</Simulation>
    """ %(str(run_num), cdf_begin, cdf_end, str(run_num), str(run_num), str(run_num))
    return input_file

def generate_jobfile(nodes, wallhour, raven_input):
    jobfile = """
#!/bin/bash
#PBS -l nodes=%s:ppn=32:xe
#PBS -N serpent-raven
#PBS -l walltime=%s:00:00
#PBS -j oe

### cd to the location where you submitted the job, if needed
### note that you are on a PBS MOM node and not running interactively on a
### compute node

cd $PBS_O_WORKDIR

# To add certain modules that you do not have added via ~/.modules
# module swap PrgEnv-cray PrgEnv-gnu
export OMP_NUM_THREADS=32

module load bwpy
export EPYTHON="python2.7"

python /projects/sciteam/bahg/projects/raven/framework/Driver.py %s
    """%(str(nodes), str(wallhour), raven_input)
    return jobfile


for num in range(1,num_splits + 1):
    raven_input_file_path = '/projects/sciteam/bahg/projects/raven/framework/CodeInterfaces/SERPENT/multiinput/%s.xml' %str(num)
    jobfile_path = raven_input_file_path.replace('.xml', '.pbs')
    with open(raven_input_file_path, 'w') as file:
        cdf_begin = cdf_dist[num - 1]
        cdf_end = cdf_dist[num]
        run_num = num
        file.write(gen_input(run_num, cdf_begin, cdf_end))
    with open(jobfile_path, 'w') as jobfile:
        jobfile.write(generate_jobfile(nodes, wallhour, raven_input_file_path))
