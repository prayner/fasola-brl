<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" indent="yes"/>

  <!-- Identity transform: copy all nodes by default -->
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>

  <!-- Template to match the specific direction element and replace it -->
  <xsl:template match="direction[other-direction='Repeat Dots']">
    <barline location="left">
      <bar-style>heavy-light</bar-style>
      <repeat direction="forward"/>
    </barline>
  </xsl:template>
<xsl:template match="direction[direction-type/other-direction = 'SH repeat dots' or direction-type/other-direction = 'Repeat Dots' or direction-type/other-direction = 'SH repeat right']">
    <barline location="left">
      <bar-style>heavy-light</bar-style>
      <repeat direction="forward"/>
    </barline>
  </xsl:template>
<xsl:template match="direction[direction-type/other-direction = 'SH repeat left' or direction-type/other-direction = 'SH coincident repeat']">
    <barline location="right">
      <bar-style>light-heavy</bar-style>
      <repeat direction="backward"/>
    </barline>
  </xsl:template>
</xsl:stylesheet>
