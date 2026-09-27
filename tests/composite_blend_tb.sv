`timescale 1ns/1ps
module composite_blend_tb;
  reg clk = 0;
  reg enable = 0;
  reg hblank = 1;
  reg vblank = 0;
  reg [23:0] rgb_in = 0;
  wire [23:0] rgb_out;
  composite_blend dut(.*);
  always #5 clk = ~clk;

  task pixel(input bit en, input bit hb, input bit vb,
             input [23:0] color, input [23:0] expected);
    begin
      @(negedge clk);
      enable = en;
      hblank = hb;
      vblank = vb;
      rgb_in = color;
      // Check the value consumed by scanline_filler at the next rising edge.
      #1;
      if (rgb_out !== expected)
        $fatal(1, "RGB %h expected %h got %h", color, expected, rgb_out);
      @(posedge clk);
      #1;
    end
  endtask

  initial begin
    pixel(0, 1, 0, 24'hffffff, 24'hffffff);
    pixel(0, 0, 0, 24'h123456, 24'h123456);
    pixel(0, 0, 0, 24'hfedcba, 24'hfedcba);
    pixel(1, 1, 0, 24'hffffff, 24'hffffff);
    pixel(1, 0, 0, 24'hfe8040, 24'h7f4020); // black left border
    pixel(1, 0, 0, 24'h0200c0, 24'h804080); // independent channels
    pixel(1, 0, 0, 24'hffffff, 24'h807fdf); // floor odd sums
    pixel(1, 0, 0, 24'hffffff, 24'hffffff); // no overflow
    pixel(1, 0, 1, 24'hffffff, 24'hffffff); // vertical blank resets history
    pixel(1, 0, 0, 24'hffffff, 24'h7f7f7f);
    pixel(0, 0, 0, 24'h010305, 24'h010305); // immediate bypass
    pixel(1, 0, 0, 24'h050709, 24'h030507); // history tracks while off
    pixel(1, 1, 0, 24'hff0000, 24'hff0000);
    pixel(1, 0, 0, 24'h000000, 24'h000000); // no preceding-line bleed
    $display("PASS: composite blend arithmetic, bypass, toggles, and line boundaries");
    $finish;
  end
endmodule
