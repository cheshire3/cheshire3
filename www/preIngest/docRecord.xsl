<?xml version="1.0"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:str="http://www.metaphoricalweb.org/xmlns/string-utilities"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                version="1.0">

    <!-- This can be used in version 2.0, but that is not the XSLT we have right now
    <xsl:function name="str:title-case-word" as="xs:string">
        <xsl:param name="token"/>
        <xsl:choose>
            <xsl:when test="$token = 'issn'">
                <xsl:value-of select="'ISSN'"/>
            </xsl:when>
            <xsl:when test="ends-with($token, 'id')">
                <xsl:value-of select="concat(str:title-case-word(substring($token, 1, string-length($token) - 2)), ' ID')"/>
            </xsl:when>
            <xsl:when test="starts-with($token, 'is')">
                <xsl:value-of select="concat('Is ', str:title-case-word(substring($token, 3)))"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="
                    concat(upper-case(substring($token,1,1)),
                              lower-case(substring($token,2)), ' ')"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:function>

    <xsl:function name="str:title-case" as="xs:string">
        <xsl:param name="expr"/>
        <xsl:variable name="tokens" select="tokenize($expr,' ')"/>
        <xsl:variable name="titledTokens" select="for $token in $tokens return
            str:title-case-word($token)"/>
        <xsl:value-of select="string-join($titledTokens,' ')"/>
    </xsl:function>
    -->

    <xsl:template match="eprint:*"
                  xmlns:eprint="http://eprints.org/ep2/data/2.0">
        <table class="docRecord">
            <xsl:for-each select="*">
                <tr>

                    <td class="attrName">
                        <!-- for version 2.0 (see above) use this instead of the one below
                        <xsl:value-of select="str:title-case(translate(local-name(), '_', ' '))"/>
                        -->
                        <xsl:value-of select="translate(local-name(), '_', ' ')"/>
                    </td>

                    <td class="attrValue">
                        <xsl:choose>
                            <xsl:when test="count(eprint:item) >= 1">
                                <xsl:choose>
                                    <xsl:when test="count(*/*) >= 1">
                                        <xsl:apply-templates select="eprint:item"/>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <xsl:for-each select="eprint:*">
                                            <xsl:value-of select="."/>
                                            <br/>
                                        </xsl:for-each>
                                    </xsl:otherwise>
                                </xsl:choose>
                            </xsl:when>
                            <xsl:when test="local-name() = 'eprint:name'">
                                <xsl:value-of select="eprint:honourific"/>
                                <xsl:value-of select="eprint:given"/>
                                <xsl:value-of select="eprint:family"/>
                                <xsl:value-of select="eprint:lineage"/>
                                <xsl:if test="count(id) > 0">
                                    &lt;<xsl:value-of select="eprint:id"/>&gt;
                                    <br/>
                                </xsl:if>
                            </xsl:when>
                            <xsl:otherwise>
                                <xsl:value-of select="current()"/>
                            </xsl:otherwise>
                        </xsl:choose>
                    </td>
                </tr>
            </xsl:for-each>
        </table>
    </xsl:template>
</xsl:stylesheet>
