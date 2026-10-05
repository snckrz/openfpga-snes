`timescale 1ns/1ps
// Cycle-by-cycle regression of the test4 RTL snapshot against the current
// implementation for modes 0..7. Mode 8 is covered by composite_blend_tb.
module composite_blend_strongplus_regression_tb;
  reg clk = 0;
  reg [3:0] mode = 0;
  reg [2:0] legacy_mode = 0;
  reg hblank_in = 1, vblank_in = 1;
  reg hsync_in = 0, vsync_in = 0, dotclk_in = 0, interlace_in = 0;
  reg [23:0] rgb_in = 0;
  wire [23:0] rgb_new, rgb_test4;
  wire hb_new, vb_new, hs_new, vs_new, dot_new;
  wire hb_test4, vb_test4, hs_test4, vs_test4, dot_test4;
  integer checks = 0;
  integer compared = 0;
  integer warmup = 16;
  integer m, line, x, width;

  composite_blend new_dut(
    .clk(clk), .mode(mode), .hblank_in(hblank_in), .vblank_in(vblank_in),
    .hsync_in(hsync_in), .vsync_in(vsync_in), .dotclk_in(dotclk_in),
    .interlace_in(interlace_in), .rgb_in(rgb_in), .rgb_out(rgb_new),
    .hblank_out(hb_new), .vblank_out(vb_new), .hsync_out(hs_new),
    .vsync_out(vs_new), .dotclk_out(dot_new));

  composite_blend_test4 test4_dut(
    .clk(clk), .mode(legacy_mode), .hblank_in(hblank_in), .vblank_in(vblank_in),
    .hsync_in(hsync_in), .vsync_in(vsync_in), .dotclk_in(dotclk_in),
    .interlace_in(interlace_in), .rgb_in(rgb_in), .rgb_out(rgb_test4),
    .hblank_out(hb_test4), .vblank_out(vb_test4), .hsync_out(hs_test4),
    .vsync_out(vs_test4), .dotclk_out(dot_test4));

  always #5 clk = ~clk;

  function automatic [23:0] color_for(input integer px, input integer ln, input integer md);
    integer r, g, b, mix;
    begin
      // Deterministic, nonperiodic channel patterns exercise signed chroma,
      // endpoint clamping, and clipping without simulator RNG differences.
      mix = (px * 1103515245 + ln * 12345 + md * 2654435761 + 1013904223);
      r = (mix ^ (mix >>> 11) ^ (px * 73)) & 255;
      g = ((mix >>> 7) ^ (ln * 89) ^ (px * 29) ^ 8'hA5) & 255;
      b = ((mix >>> 15) ^ (md * 97) ^ (px * 137) ^ 8'h3C) & 255;
      color_for = {r[7:0], g[7:0], b[7:0]};
    end
  endfunction

  task automatic tick;
    begin
      @(posedge clk);
      #1;
      checks = checks + 1;
      if (checks > warmup) begin
        if (rgb_new !== rgb_test4 || hb_new !== hb_test4 || vb_new !== vb_test4 ||
            hs_new !== hs_test4 || vs_new !== vs_test4 || dot_new !== dot_test4)
          $fatal(1, "test4/current mismatch check=%0d mode=%0d rgb=%06h/%06h hb=%b/%b vb=%b/%b hs=%b/%b vs=%b/%b dot=%b/%b",
                 checks, mode, rgb_test4, rgb_new, hb_test4, hb_new, vb_test4, vb_new,
                 hs_test4, hs_new, vs_test4, vs_new, dot_test4, dot_new);
        compared = compared + 1;
      end
    end
  endtask

  task automatic send(input [23:0] color, input bit hb, vb, hs, vs, dotc, intl);
    begin
      @(negedge clk);
      rgb_in = color;
      hblank_in = hb;
      vblank_in = vb;
      hsync_in = hs;
      vsync_in = vs;
      dotclk_in = dotc;
      interlace_in = intl;
      legacy_mode = mode[2:0];
      tick();
    end
  endtask

  task automatic frame_edge(input bit intl);
    begin
      send(24'h000000, 1, 1, 0, 0, 0, intl);
      send(24'h000000, 1, 1, 0, 1, 0, intl);
      send(24'h000000, 1, 0, 0, 0, 0, intl);
    end
  endtask

  initial begin
    // Initialize both designs and allow their pipelines/history to settle.
    mode = 0;
    legacy_mode = 0;
    repeat (warmup + 2) send(24'h000000, 1, 1, 0, 0, 0, 0);
    send(24'h000000, 1, 0, 0, 0, 0, 0);

    // Exercise every legacy mode. Deliberately switch modes without an
    // intervening frame as well as at frame boundaries to compare invalidation.
    for (m = 0; m <= 7; m = m + 1) begin
      mode = m[3:0];
      legacy_mode = m[2:0];
      if ((m % 2) == 0) frame_edge((m >> 1) & 1);
      for (line = 0; line < 5; line = line + 1) begin
        case (line)
          0: width = 1;
          1: width = 3;
          2: width = 24;
          3: width = 256;
          default: width = 512;
        endcase
        send(24'h000000, 1, 0, 0, (line == 4), 0, ((m + line) & 1));
        for (x = 0; x < width; x = x + 1)
          send(color_for(x, line + m * 7, m), 0, 0,
               (x & 7) == 0, (line == 4) && (x == width - 1), (x & 1), ((m + line) & 1));
        // Drain the line and vary blanking/sync metadata through the pipeline.
        send(24'hffffff, 1, 0, 1, 0, 1, ((m + line) & 1));
        send(24'h123456, 1, 0, 0, 0, 0, ((m + line) & 1));
      end
    end

    // Alternating interlace settings and explicit frame transitions after all
    // modes ensure both instances respond identically to history resets.
    mode = 7;
    legacy_mode = 7;
    frame_edge(0);
    send(24'hff00ff, 1, 0, 0, 0, 0, 1);
    send(24'h00ff00, 1, 0, 0, 0, 0, 1);
    frame_edge(1);
    send(24'h7b2de5, 1, 0, 0, 0, 1, 0);

    if (compared < 1000)
      $fatal(1, "insufficient paired RTL coverage: %0d compared cycles", compared);
    $display("PASS: test4/current modes 0..7 matched for %0d cycles (%0d startup cycles skipped)", compared, warmup);
    $finish;
  end
endmodule
