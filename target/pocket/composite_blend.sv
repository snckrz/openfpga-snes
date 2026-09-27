// Composite-like horizontal averaging adapted from Kitrinx's cofi.sv in
// opengateware/openFPGA-Genesis. This is an RGB blend, not an NTSC encoder.
// Combinational output preserves the existing Pocket sync/blanking timing.
module composite_blend (
    input wire clk,
    input wire enable,
    input wire hblank,
    input wire vblank,
    input wire [23:0] rgb_in,
    output wire [23:0] rgb_out
);
  reg [23:0] previous = 0;
  reg previous_blank = 1;
  wire blank = hblank | vblank;

  function automatic [7:0] average(input [7:0] a, input [7:0] b);
    reg [8:0] sum;
    begin
      sum = {1'b0, a} + {1'b0, b};
      average = sum[8:1];
    end
  endfunction

  // Match cofi's black left neighbor at the beginning of each active line.
  wire [23:0] left_pixel = previous_blank ? 24'b0 : previous;
  assign rgb_out = (!enable || blank) ? rgb_in : {
      average(left_pixel[23:16], rgb_in[23:16]),
      average(left_pixel[15:8], rgb_in[15:8]),
      average(left_pixel[7:0], rgb_in[7:0])
  };

  always @(posedge clk) begin
    previous <= rgb_in;
    previous_blank <= blank;
  end
endmodule
