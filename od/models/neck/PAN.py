import torch.nn as nn
from od.models.modules.common import BottleneckCSP, Conv, Concat
from utils.general import make_divisible


class PAN(nn.Module):
    """
        This PAN  refer to yolov5, there are many different versions of implementation, and the details will be different.
        默认的输出通道数设置成了yolov5L的输出通道数, 当backbone为YOLOV5时，会根据version对输出通道转为了YOLOv5 对应版本的输出。对于其他backbone，使用的默认值.


    P3 --->  PP3
    ^         |
    | concat  V
    P4 --->  PP4
    ^         |
    | concat  V
    P5 --->  PP5
    """

    def __init__(self,P2_size =192, P3_size=512, P4_size=256, P5_size=512,inner_p2 =128, inner_p3=256, inner_p4=512, inner_p5=1024, version='L'):
        super(PAN, self).__init__()
        self.version = str(version)
        gains = {'s': {'gd': 0.33, 'gw': 0.5},
                 'm': {'gd': 0.67, 'gw': 0.75},
                 'l': {'gd': 1, 'gw': 1},
                 'x': {'gd': 1.33, 'gw': 1.25}}

        if self.version.lower() in gains:
            # only for yolov5
            self.gd = gains[self.version.lower()]['gd']  # depth gain
            self.gw = gains[self.version.lower()]['gw']  # width gain
        else:
            self.gd = 1
            self.gw = 1

        self.channels_out = {
            'inner_p2': inner_p2,
            'inner_p3': inner_p3,
            'inner_p4': inner_p4,
            'inner_p5': inner_p5
        }
        self.re_channels_out()
        self.P2_size = P2_size
        self.P3_size = P3_size
        self.P4_size = P4_size
        self.P5_size = P5_size
        self.inner_p2 = self.channels_out['inner_p2']
        self.inner_p3 = self.channels_out['inner_p3']
        self.inner_p4 = self.channels_out['inner_p4']
        self.inner_p5 = self.channels_out['inner_p5']
        self.P2 = BottleneckCSP(self.P2_size , self.inner_p2, self.get_depth(3),False)
        self.convP2 = Conv(self.inner_p2, self.inner_p2, 3, 2)

        self.P3 = BottleneckCSP(self.P3_size+self.inner_p2, self.inner_p3, self.get_depth(3), False)
        self.convP3 = Conv(self.inner_p3, self.inner_p3, 3, 2)
        self.P4 = BottleneckCSP(self.P4_size + self.inner_p3, self.inner_p4, self.get_depth(3), False)
        self.convP4 = Conv(self.inner_p4, self.inner_p4, 3, 2)
        self.P5 = BottleneckCSP(self.inner_p4 + P5_size, self.inner_p5, self.get_depth(3), False)
        self.concat = Concat()
        self.out_shape = (self.inner_p2,self.inner_p3, self.inner_p4, self.inner_p5)
        print("PAN input channel size: P2 {} P3 {}, P4 {}, P5 {}".format(self.P2_size ,self.P3_size, self.P4_size, self.P5_size))
        print("PAN output channel size: PP2 {} PP3 {}, PP4 {}, PP5 {}".format(self.inner_p2, self.inner_p3, self.inner_p4, self.inner_p5))

    def get_depth(self, n):
        return max(round(n * self.gd), 1) if n > 1 else n

    def get_width(self, n):
        return make_divisible(n * self.gw, 8)

    def re_channels_out(self):
        for k, v in self.channels_out.items():
            self.channels_out[k] = self.get_width(v)

    def forward(self, inputs):
        P2 , P3, P4, P5 = inputs
        # import pdb
        # pdb.set_trace()
        PP2 = self.P2(P2)
        PP2_1 = self.convP2(PP2)
        concat2_3 = self.concat([PP2_1, P3])

        PP3 = self.P3(concat2_3)
        convp3 = self.convP3(PP3)
        concat3_4 = self.concat([convp3, P4])
        PP4 = self.P4(concat3_4)
        convp4 = self.convP4(PP4)
        concat4_5 = self.concat([convp4, P5])
        PP5 = self.P5(concat4_5)
        return PP2 , PP3, PP4, PP5
